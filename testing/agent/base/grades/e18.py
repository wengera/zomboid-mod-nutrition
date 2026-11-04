"""grades.e18 -- the chain sessions' grade, pass 18 (Plan 28 Task 4): `grade_e18` is `grades.e17.grade_e17` under
"grade_e18" with the plan's second metric and the readings of survival iteration 21 (Plan 28 Task 3, `T11_SWITCHES`),
each read off the frames, the decision log's why fields, the artifact's actions and stop and the state log's act lines
and events:

  hits         P28-M, the hits per kill: the `me.hitReaction` runs, their kinds, their count over the kills, the wounds
               (the rises of `body.scratched`, `body.bitten` and `body.bleeding`) per kill, the runs by fight and the
               strike sent within STRIKE_BEFORE_S before each. Read off the frames alone, a decision log or none.
  wound_dress  P28-A, the wound dressed (`WOUND_DRESS`): the dressings sent for the `wound` reason, done, by part, the
               part's health across them, the `wound_held` lines, the health fallen quiet on an undressed wound.
  shove_back   P28-B2, the back leg after a missed shove (`SHOVE_BACK`): the legs, the bites during them, the shoves
               after them.
  drift_stand  P28-B3, the drifted pin's stance (`DRIFT_STAND`): the legs, the shoves after, the bites after.
  floor_pain   P28-C, the floor swing under the arms' pain (`FLOOR_PAIN`): the swings at or over STRAIN_HARD, landed,
               their kills, the stomps after, and an older log's floor swings under the pain (the check, 0 by P24-AP).
  busy_retry   P28-D, a `busy` rejection retried (`BUSY_RETRY`): the sends by kind, the stomps landed after, the kills.
  circle       P28-E, the circle (`CIRCLE`): the `back` legs by the turn's side, the sides switched, the turns off
               CIRCLE_TURN, the straight `back` legs at two or more standing zombies within KEEP_R.
  facing       P28-F, the facing on the swing (the F11 guide's section 2 read, graded): on the frame after each attack's
               swing event the compass points between `me.dir` and the target's bearing, the shoves' and stomps' apart.
  client_end   the spec's 1 (c), the client's end as a stop: the stop's reason and `loop.end`'s seq and health.

Each reading but `hits` is {"read": False} without a decision log; `hits` is {"read": False} without frames. A key
marked reading counts what the log, the frames or the artifact states; one marked inference reads an effect off the
frames, the events or the order of lines. Every live planner name the readings read is copied below as a frozen
constant with its source and its value at 8e5d26f1 (ruling P26-Q, `grades/__init__.py`; WOUND_RESERVE and CIRCLE_TURN
as Plan 28 Task 3's brief names them, `planner/policies.py`'s table after WALK_DONE_R): this module imports nothing
from `agent.base.planner` or `agent.base.world`; the chain it imports (`grades.e17.grade_e17`, which reads live names
through `e16`, `e15`, `e14` and `gates_e`) is pinned by the regrade tests of the artifacts graded through it. Frozen
once an artifact carries its output; `gates_e`, `grades/e14.py` to `grades/e17.py` and every driver stay untouched."""
import bisect
import math

from agent.base import gates_e as E
from agent.base.grades import e14 as G14
from agent.base.grades import e17 as G17

# Frozen copies of the live planner names read here (P26-Q), each as it stood at 8e5d26f1 (Plan 28 Task 2's head).
STRAIN_HARD = 20.0     # planner/policies.py:166: the arms' summed pain at which the Fight never swings (P24-AP)
KEEP_R = 2.5           # planner/policies.py:134: tiles, a target inside this is backpedalled from (the circle's count)
AIM_LEG_S = 2.0        # planner/policies.py:130: seconds one stance leg (`aim`) holds
WOUND_RESERVE = 1      # planner/policies.py (Plan 28 Task 3, P28-A): clean dressings the wound step keeps back
CIRCLE_TURN = 45.0     # planner/policies.py (Plan 28 Task 3, P28-E): degrees the circle turns the `back` heading
COMPASS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")   # world.py:213: the eight points, clockwise from north


def bearing_deg(dx, dy):
    """world.py:232 `bearing_deg`, copied: the bearing of the offset (dx, dy), degrees clockwise from north (-y), in
    [0, 360); None for no offset."""
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return None
    return math.degrees(math.atan2(dx, -dy)) % 360.0


def compass(dx, dy):
    """world.py:239 `compass`, copied: the eighth of the compass (N, NE, ... NW) the offset (dx, dy) points into (world
    x east, y south), None for no offset."""
    b = bearing_deg(dx, dy)
    return None if b is None else COMPASS[int((b + 22.5) // 45.0) % 8]


FOLLOW_LINES = G17.FOLLOW_LINES   # log lines a send's follow-up is read this far on (e17's)
BITE_AFTER_S = G17.BITE_AFTER_S   # wall seconds a bite is read after a leg (e17's)
STRIKE_BEFORE_S = 2.0             # wall seconds before a reaction run's first frame its strike is read (P28-M)
STRIKES = ("shove", "attack", "stomp")
WOUND_COUNTS = ("scratched", "bitten", "bleeding")
NEW = ("hits", "wound_dress", "shove_back", "drift_stand", "floor_pain", "busy_retry", "circle", "facing",
       "client_end")


def _wall(ln):
    """The decision-log line's wall in ms."""
    return (E._n(ln.get("wall")) or 0.0) * 1000.0


def _any_in(walls, lo, hi):
    """Whether a value of the sorted `walls` lies in lo..hi."""
    i = bisect.bisect_left(walls, lo)
    return i < len(walls) and walls[i] <= hi


# ---------------------------------------------------------------- P28-M
def _reaction(f):
    """The frame's `me.hitReaction` when a non-empty string, else None."""
    h = E._d(E._d(f).get("me")).get("hitReaction")
    return h if isinstance(h, str) and h else None


def _hit_runs(frames):
    """The first frames of the reaction runs of `frames` (in wall order): a run starts on a frame reading
    `me.hitReaction` a non-empty string after one reading it empty or None (the first frame counts as after None)."""
    runs, prev = [], None
    for f in frames:
        h = _reaction(f)
        if h is not None and prev is None:
            runs.append(f)
        prev = h
    return runs


def _run_walls(lines):
    """The sorted wallMs of the reaction runs' first frames (`_hit_runs`)."""
    return [E._n(f.get("wallMs")) for f in _hit_runs(E._frame_index(lines)[1])]


def _wound_rises(frames):
    """(summed rises, frames on which one rose) of WOUND_COUNTS between consecutive frames."""
    total, n = 0, 0
    for f0, f1 in zip(frames, frames[1:]):
        b0, b1 = E._d(E._d(f0).get("body")), E._d(E._d(f1).get("body"))
        r = sum(max(0, (E._n(b1.get(k)) or 0) - (E._n(b0.get(k)) or 0)) for k in WOUND_COUNTS)
        total += r
        n += 1 if r > 0 else 0
    return total, n


def _in_span(fight, t):
    """Whether loop second `t` lies in the fight's span (`startS` to `end.endS`, open without an end)."""
    s, e = E._n(fight.get("startS")), E._n(E._d(fight.get("end")).get("endS"))
    return t is not None and s is not None and t >= s and (e is None or t <= e)


def _accepts(lines):
    """([wallMs], [act line]) of the state log's accepted act lines of the STRIKES types, sorted by wallMs."""
    rows = sorted(((E._n(ln.get("wallMs")), ln) for ln in E._l(lines)
                   if isinstance(ln, dict) and ln.get("kind") == "act" and ln.get("state") == "accepted"
                   and ln.get("type") in STRIKES and E._n(ln.get("wallMs")) is not None), key=lambda p: p[0])
    return [w for w, _ in rows], [a for _, a in rows]


def _zd(f, z):
    """The zombie's distance off the frame's player position, else its `dist`."""
    me, z = E._d(E._d(f).get("me")), E._d(z)
    mx, my, zx, zy = E._n(me.get("x")), E._n(me.get("y")), E._n(z.get("x")), E._n(z.get("y"))
    return math.hypot(zx - mx, zy - my) if None not in (mx, my, zx, zy) else E._n(z.get("dist"))


def _nearest_standing(f):
    """The id of the frame's nearest zombie not read fallen, else None."""
    zs = [(d, E._d(z).get("id")) for z in E._l(E._d(f).get("zombies")) if E._d(z).get("onFloor") is not True
          for d in [_zd(f, z)] if d is not None]
    return min(zs, key=lambda p: p[0])[1] if zs else None


def _strike_before(acc, ends, targets, f):
    """The run at frame `f`'s strike (an inference off the order of lines): the last accepted STRIKES act line within
    STRIKE_BEFORE_S before the frame, its type, aid, seconds before, target, whether the target was the frame's
    nearest standing zombie, and its terminal line's `knockdown` and `attackStarted`; type None without one."""
    walls, rows = acc
    w = E._n(f.get("wallMs"))
    i = bisect.bisect_right(walls, w) - 1 if w is not None else -1
    got = {"seq": f.get("seq"), "kind": _reaction(f), "type": None, "aid": None, "before_s": None, "target": None,
           "nearest": None, "knockdown": None, "attackStarted": None}
    if i < 0 or walls[i] < w - STRIKE_BEFORE_S * 1000.0:
        return got
    a = rows[i]
    r = E._d(E._d(ends.get(a.get("aid"))).get("result"))
    zid = targets.get(a.get("aid"))
    got.update(type=a.get("type"), aid=a.get("aid"), before_s=round((w - walls[i]) / 1000.0, 3), target=zid,
               nearest=zid is not None and _nearest_standing(f) == zid, knockdown=r.get("knockdown"),
               attackStarted=r.get("attackStarted"))
    return got


def _ends(lines):
    """{aid: terminal act line} of the STRIKES act lines."""
    out = {}
    for kind in STRIKES:
        out.update({aid: end for aid, (_, end) in G14._acts(lines, kind).items() if end is not None})
    return out


def _targets(out):
    """{aid: targetId} of the artifact's loop.actions."""
    return {a.get("aid"): E._d(a.get("args")).get("targetId")
            for a in (E._d(x) for x in E._l(E._d(E._d(out).get("loop")).get("actions")))}


def e_hits(out, lines, kills):
    """The hits per kill (P28-M, ruling of 2026-11-04): {read, runs, kills, per_kill, wounds, wound_frames,
    wounds_per_kill, by_fight, outside, kinds, strike_before}, read off the frames with or without a decision log
    ({"read": False} without a frame). Reading: `runs` the reaction runs (`_hit_runs`), `kinds` the first frame's
    reaction per run, `kills` the inherited `kills.planner`, `per_kill` runs over it (None at 0 kills), `wounds` the
    summed rises of WOUND_COUNTS between consecutive frames on `wound_frames` frames, `wounds_per_kill` over the kills,
    `by_fight` the runs whose first frame lies in each `loop.fights` row's span (`startS` to `end.endS` on the loop
    clock), `outside` those in none. Inference off the order of lines: `strike_before` per run (`_strike_before`)."""
    _, frames = E._frame_index(lines)
    if not frames:
        return {"read": False}
    runs = _hit_runs(frames)
    kinds = {}
    for f in runs:
        G14._inc(kinds, _reaction(f))
    wounds, wound_frames = _wound_rises(frames)
    k = E._n(kills) or 0
    per = lambda n: n / k if k else None     # noqa: E731
    fights = [E._d(x) for x in E._l(E._d(E._d(out).get("loop")).get("fights")) if isinstance(x, dict)]
    t0 = E._loop_start_s(out)
    by, outside = [0] * len(fights), 0
    for f in runs:
        w = E._n(f.get("wallMs"))
        t = w / 1000.0 - t0 if w is not None and t0 is not None else None
        i = next((j for j, fi in enumerate(fights) if _in_span(fi, t)), None)
        if i is None:
            outside += 1
        else:
            by[i] += 1
    acc, ends, targets = _accepts(lines), _ends(lines), _targets(out)
    return {"read": True, "runs": len(runs), "kills": k, "per_kill": per(len(runs)), "wounds": wounds,
            "wound_frames": wound_frames, "wounds_per_kill": per(wounds), "by_fight": by, "outside": outside,
            "kinds": kinds, "strike_before": [_strike_before(acc, ends, targets, f) for f in runs]}


# ---------------------------------------------------------------- P28-A
def _parts(f):
    return [E._d(p) for p in E._l(E._d(E._d(f).get("body")).get("parts"))]


def _undressed(f):
    """The indices of the frame's parts reading `wound` true and not `bandaged` (an older log's `wound` None reads
    none)."""
    return [p.get("i") for p in _parts(f) if p.get("wound") is True and p.get("bandaged") is not True]


def _quiet(f):
    """Whether the frame reads no part bleeding (nor the `bleeding` count) and no hit reaction."""
    bled = any(p.get("bleeding") is True for p in _parts(f)) or bool(E._n(E._d(E._d(f).get("body")).get("bleeding")))
    return not bled and _reaction(f) is None


def _health(f):
    return E._n(E._d(E._d(f).get("body")).get("health"))


def _part_h(f, part):
    return next((E._n(p.get("h")) for p in _parts(f) if p.get("i") == part), None)


def _done(row, acts):
    """Whether the loop.actions row ended `done`: its terminal act line's state, else the row's."""
    if row is None:
        return False
    end = acts.get(row.get("aid"), (None, None))[1]
    return (end.get("state") if end is not None else row.get("state")) == "done"


def e_wound_dress(L, lines):
    """The wound dressed (P28-A, `Survive.WOUND_DRESS`): {read, sent, done, by_part, part_h, held, held_over_reserve,
    no_bleed_fall, parts_undressed_at_end}. Reading: `sent` the care lines sending the `bandage` for the care why's
    `wound` reason {part, item, kind, h} (`care.Care.choose`'s wound step), `done` those whose action ended `done`,
    `by_part` them by part, `part_h` per part its `h` on the first send's frame and on the last frame, `held` the lines
    whose care why carries `wound_held` {part, clean}, `held_over_reserve` those whose `clean` reads over WOUND_RESERVE
    (must read 0: the step holds only at the reserve), `parts_undressed_at_end` the last frame's parts reading `wound`
    true and not bandaged. Inference off the frames: `no_bleed_fall` the health fallen across the consecutive frames
    both reading no bleed and no hit reaction whose first reads an undressed wound (`_undressed`)."""
    if L is None:
        return {"read": False}
    acts = G14._acts(lines, "bandage")
    sent = done = held = over = 0
    by, part_h = {}, {}
    for ln in L.rows:
        c = E._bw(ln, "care")
        wh = c.get("wound_held")
        if isinstance(wh, dict):
            held += 1
            cl = E._n(wh.get("clean"))
            over += 1 if cl is not None and cl > WOUND_RESERVE else 0
        if ln.get("branch") != "care" or c.get("reason") != "wound" or not E._sent(ln, "bandage"):
            continue
        sent += 1
        p = c.get("part")
        G14._inc(by, str(p))
        done += 1 if _done(L.action(ln), acts) else 0
        if str(p) not in part_h:
            part_h[str(p)] = [_part_h(L.frame(ln), p), p]
    _, frames = L.index
    last = frames[-1] if frames else None
    for v in part_h.values():
        v[1] = _part_h(last, v[1])
    fall = 0.0
    for f0, f1 in zip(frames, frames[1:]):
        h0, h1 = _health(f0), _health(f1)
        if h0 is None or h1 is None or not (_quiet(f0) and _quiet(f1)) or not _undressed(f0):
            continue
        fall += max(0.0, h0 - h1)
    return {"read": True, "sent": sent, "done": done, "by_part": by, "part_h": part_h, "held": held,
            "held_over_reserve": over, "no_bleed_fall": fall,
            "parts_undressed_at_end": sorted(_undressed(last)) if last is not None else []}


# ---------------------------------------------------------------- P28-B2
def e_shove_back(L, lines):
    """The back leg after a missed shove (P28-B2, `Threat.SHOVE_BACK`): {read, lines, legs, bites_during,
    shoves_after}. Reading: `lines` the threat lines whose why carries `shove_back` {target, missed}
    (`shove.FightShove._shove`, the stance's `back` leg in the second shove's place), `legs` those that sent the
    `aim`. Inference off the frames and the order of lines: `bites_during` the legs during which (from the send to the
    action's end, else AIM_LEG_S on) a hit reaction run began, `shoves_after` the legs followed within FOLLOW_LINES by
    a shove sent at the same zombie."""
    if L is None:
        return {"read": False}
    acts, runs, rows = G14._acts(lines, "aim"), _run_walls(lines), L.rows
    n = legs = during = after = 0
    for i, ln in enumerate(rows):
        sb = L.why(ln).get("shove_back") if ln.get("branch") == "threat" else None
        if not isinstance(sb, dict):
            continue
        n += 1
        if not E._sent(ln, "aim"):
            continue
        legs += 1
        w, row = _wall(ln), L.action(ln)
        end = G14._end_ms(L, row, acts) if row is not None else None
        hi = end if end is not None else w + AIM_LEG_S * 1000.0
        during += 1 if _any_in(runs, w, hi) else 0
        zid = sb.get("target")
        after += 1 if G17._after(rows, i, lambda r: E._sent(r, "shove") and G17._target(r) == zid) else 0
    return {"read": True, "lines": n, "legs": legs, "bites_during": during, "shoves_after": after}


# ---------------------------------------------------------------- P28-B3
def _drift_leg(w):
    """Whether the threat why is P28-B3's: `out_of_reach` true with `stance` true and `leg` "stand"."""
    return w.get("out_of_reach") is True and w.get("stance") is True and w.get("leg") == "stand"


def e_drift_stand(L, lines):
    """The drifted pin's stance (P28-B3, `Threat.DRIFT_STAND`): {read, lines, legs, shoves_after, bites_after}.
    Reading: `lines` the threat lines whose why reads `out_of_reach` true with `stance` true and `leg` "stand"
    (`fight.Fight._choose`'s cornered branch, the pin beyond CORNERED_R chasing), `legs` those that sent the `aim`.
    Inference off the frames and the order of lines: `shoves_after` the legs followed within FOLLOW_LINES by a shove
    at the why's target, `bites_after` those after which a hit reaction run began within BITE_AFTER_S."""
    if L is None:
        return {"read": False}
    runs, rows = _run_walls(lines), L.rows
    n = legs = after = bites = 0
    for i, ln in enumerate(rows):
        w = L.why(ln)
        if ln.get("branch") != "threat" or not _drift_leg(w):
            continue
        n += 1
        if not E._sent(ln, "aim"):
            continue
        legs += 1
        zid = w.get("target")
        after += 1 if G17._after(rows, i, lambda r: E._sent(r, "shove") and G17._target(r) == zid) else 0
        wm = _wall(ln)
        bites += 1 if _any_in(runs, wm, wm + BITE_AFTER_S * 1000.0) else 0
    return {"read": True, "lines": n, "legs": legs, "shoves_after": after, "bites_after": bites}


# ---------------------------------------------------------------- P28-C
def e_floor_pain(L, lines):
    """The floor swing under the arms' pain (P28-C, `Threat.FLOOR_PAIN`): {read, swings, landed, kills, stomps_after,
    swings_under_pain_before}. Reading: `swings` the threat lines sending the `attack` whose why's `floor_finish`
    {target, health, pain} reads `pain` at or over STRAIN_HARD (`finish.FightFinish._floor_finish` and the flee's
    finish), `kills` the zombies their results read dead; `swings_under_pain_before` the floor swings sent whose why
    carries no `pain` (an older log's) on a frame reading `body.armPain` at or over STRAIN_HARD (the check: 0 by
    construction, P24-AP barred them). Inference off the events and the order of lines: `landed` the swings with a
    `swing` event in their act (`grades.e17._swung`), `stomps_after` those followed within FOLLOW_LINES by a stomp at
    the same zombie."""
    if L is None:
        return {"read": False}
    acts, swings, rows = G14._acts(lines, "attack"), G17._swing_walls(lines), L.rows
    landed = after = before = 0
    sent = []
    for i, ln in enumerate(rows):
        ff = L.why(ln).get("floor_finish") if ln.get("branch") == "threat" else None
        if not isinstance(ff, dict) or not E._sent(ln, "attack"):
            continue
        p = E._n(ff.get("pain"))
        if p is None:
            f = L.frame(ln)
            ap = E._n(E._d(E._d(f).get("body")).get("armPain")) if f is not None else None
            before += 1 if ap is not None and ap >= STRAIN_HARD else 0
            continue
        if p < STRAIN_HARD:
            continue
        sent.append(ln)
        landed += 1 if G17._swung(L, ln, L.action(ln), acts, swings) else 0
        zid = G17._target(ln)
        after += 1 if G17._after(rows, i, lambda r: E._sent(r, "stomp") and G17._target(r) == zid) else 0
    return {"read": True, "swings": len(sent), "landed": landed, "kills": len(L.kill_ids(sent)), "stomps_after": after,
            "swings_under_pain_before": before}


# ---------------------------------------------------------------- P28-D
def _hit(L, ln):
    """Whether the line's sent action's result reads `hit` true."""
    row = L.action(ln)
    return row is not None and L.res.get(row.get("aid"), {}).get("hit") is True


def e_busy_retry(L):
    """A `busy` rejection retried (P28-D, `Threat.BUSY_RETRY`): {read, sends, by_kind, stomps_landed_after,
    kills_after}. Reading: `sends` the threat lines whose why carries `busy_retry` {target, kind} that sent that kind
    (`fight.Fight._choose`, the tick the rejected send goes again), `by_kind` them by kind. Inference off the order of
    lines: `stomps_landed_after` the retries for which a stomp at the same zombie, on the line or within FOLLOW_LINES
    after it, read `hit` true, `kills_after` those whose zombie a send on the line or within FOLLOW_LINES killed."""
    if L is None:
        return {"read": False}
    rows = L.rows
    sends = landed = kills = 0
    by = {}
    for i, ln in enumerate(rows):
        br = L.why(ln).get("busy_retry") if ln.get("branch") == "threat" else None
        if not isinstance(br, dict):
            continue
        kind = br.get("kind")
        if not E._sent(ln, kind):
            continue
        sends += 1
        G14._inc(by, str(kind))
        zid, span = br.get("target"), rows[i:i + 1 + FOLLOW_LINES]
        landed += 1 if any(E._sent(r, "stomp") and G17._target(r) == zid and _hit(L, r) for r in span) else 0
        kills += 1 if any(L.killed(r) == zid for r in span) else 0
    return {"read": True, "sends": sends, "by_kind": by, "stomps_landed_after": landed, "kills_after": kills}


# ---------------------------------------------------------------- P28-E
def _standing_within(f, r):
    """The frame's zombies not read fallen within `r` tiles (`_zd`)."""
    return sum(1 for z in E._l(E._d(f).get("zombies")) for d in [_zd(f, z)]
               if E._d(z).get("onFloor") is not True and d is not None and d <= r)


def e_circle(L):
    """The circle (P28-E, `Threat.CIRCLE`): {read, legs, sides, blocked_turns, off_turn, straight_two}. Reading: `legs`
    the threat lines sending the `aim` on the `back` leg whose why carries `circle` {turn} (`fight.Fight._circle_turn`),
    `sides` them by the turn's sign ("+", "-", "0"), `off_turn` those whose turn is not CIRCLE_TURN either way (must
    read 0). Inference off the order of lines and the frames: `blocked_turns` the legs whose side differs from the
    previous circle leg's (the kept side read blocked: `_circle_turn` keeps its side while its heading is clear),
    `straight_two` the `back` legs sent without `circle` whose frame reads two or more standing zombies within KEEP_R
    (the straight backpedal the rule keeps)."""
    if L is None:
        return {"read": False}
    legs = blocked = off = straight = 0
    sides, last = {}, None
    for ln in L.rows:
        if ln.get("branch") != "threat":
            continue
        w = L.why(ln)
        if w.get("leg") != "back" or not E._sent(ln, "aim"):
            continue
        c = w.get("circle")
        if not isinstance(c, dict):
            f = L.frame(ln)
            straight += 1 if f is not None and _standing_within(f, KEEP_R) >= 2 else 0
            continue
        legs += 1
        t = E._n(c.get("turn"))
        side = "+" if t is not None and t > 0 else "-" if t is not None and t < 0 else "0"
        G14._inc(sides, side)
        off += 1 if t is None or abs(abs(t) - CIRCLE_TURN) > 1e-9 else 0
        blocked += 1 if last is not None and side != last else 0
        last = side
    return {"read": True, "legs": legs, "sides": sides, "blocked_turns": blocked, "off_turn": off,
            "straight_two": straight}


# ---------------------------------------------------------------- P28-F
def _points(d, b):
    """The compass points (0 to 4) between the facing `d` and the bearing `b`, None when either is not a point."""
    if d not in COMPASS or b not in COMPASS:
        return None
    i = (COMPASS.index(d) - COMPASS.index(b)) % 8
    return min(i, 8 - i)


def _facing_off(f, zid):
    """The points between the frame's `me.dir` and the bearing of zombie `zid` on it, else None."""
    me = E._d(E._d(f).get("me"))
    z = next((E._d(q) for q in E._l(E._d(f).get("zombies")) if E._d(q).get("id") == zid), None)
    mx, my = E._n(me.get("x")), E._n(me.get("y"))
    zx, zy = (E._n(z.get("x")), E._n(z.get("y"))) if z is not None else (None, None)
    if None in (mx, my, zx, zy):
        return None
    return _points(me.get("dir"), compass(zx - mx, zy - my))


def e_facing(L, out, lines):
    """The facing on the swing (P28-F, the F11 guide's section 2 read): {read, swings, off_by_points, unread,
    shoves_off, stomps_off}. Inference off the order of lines: each started `swing` event (`attackStarted` true) is the
    act of the last accepted act line before it in the state log. Reading, on the first frame after each event:
    `off_by_points` the attacks' events by the compass points (0 to 4) between `me.dir` and the bearing of the act's
    target (world x east, y south, `compass`), `unread` those whose frame lists no target or reads no point, `swings`
    the attacks' events; `shoves_off` and `stomps_off` the same over the shoves' and the stomps' events (the
    comparison)."""
    if L is None:
        return {"read": False}
    targets = _targets(out)
    tally = {t: {"swings": 0, "off_by_points": {str(i): 0 for i in range(5)}, "unread": 0} for t in STRIKES}
    pend, last = [], None
    for ln in E._l(lines):
        if not isinstance(ln, dict):
            continue
        k = ln.get("kind")
        if k == "act" and ln.get("state") == "accepted":
            last = ln
        elif k == "event" and ln.get("event") == "swing" and ln.get("attackStarted") is True:
            pend.append(last)
        elif k == "frame" and pend:
            for a in pend:
                t = E._d(a).get("type")
                if t not in tally:
                    continue
                tally[t]["swings"] += 1
                off = _facing_off(ln, targets.get(E._d(a).get("aid")))
                if off is None:
                    tally[t]["unread"] += 1
                else:
                    tally[t]["off_by_points"][str(off)] += 1
            pend = []
    a = tally["attack"]
    return {"read": True, "swings": a["swings"], "off_by_points": a["off_by_points"], "unread": a["unread"],
            "shoves_off": tally["shove"], "stomps_off": tally["stomp"]}


# ---------------------------------------------------------------- the spec's 1 (c)
def e_client_end(out, L):
    """The client's end as a stop (the spec's 1 (c), Plan 28 Task 1's `client_end`): {read, stopped, seq, health}.
    Reading: `stopped` the artifact's `stop.reason`, `seq` and `health` its `loop.end`'s (written at a `client_end`
    stop; None on an artifact from before Task 1 or another stop)."""
    if L is None:
        return {"read": False}
    end = E._d(E._d(E._d(out).get("loop")).get("end"))
    return {"read": True, "stopped": E._d(E._d(out).get("stop")).get("reason"), "seq": end.get("seq"),
            "health": end.get("health")}


def readings_e18(out, decision_lines, lines, kills=None):
    """{key: reading} of the nine readings (`NEW`): `hits` off the frames (over `kills`, the inherited
    `kills.planner`, else `gates_e.e_kills_9`'s), every other {"read": False} without a decision log."""
    out = E._d(out)
    L = E._Lines(out, decision_lines, lines) if decision_lines is not None else None
    if kills is None:
        kills = E.e_kills_9(out, lines).get("planner")
    return {"hits": e_hits(out, lines, kills), "wound_dress": e_wound_dress(L, lines),
            "shove_back": e_shove_back(L, lines), "drift_stand": e_drift_stand(L, lines),
            "floor_pain": e_floor_pain(L, lines), "busy_retry": e_busy_retry(L), "circle": e_circle(L),
            "facing": e_facing(L, out, lines), "client_end": e_client_end(out, L)}


def lines_e18(g):
    """One report line per pass 18 reading, each clause marked reading or inference."""
    hi, wd, sb, ds, fp, br, ci, fa, ce = (E._d(g.get(k)) for k in NEW)
    out = []
    strikes = {}
    for s in E._l(hi.get("strike_before")):
        G14._inc(strikes, str(E._d(s).get("type")))
    out.append(("hits (P28-M) [reading]: %s reaction runs %s over %s kills (%s a kill), %s wounds on %s frames (%s a "
                "kill), by fight %s, %s outside a fight; [inference] the strike within STRIKE_BEFORE_S before each "
                "by type %s" % (hi.get("runs"), hi.get("kinds"), hi.get("kills"), hi.get("per_kill"), hi.get("wounds"),
                                hi.get("wound_frames"), hi.get("wounds_per_kill"), hi.get("by_fight"),
                                hi.get("outside"), strikes)) if hi.get("read")
               else "hits (P28-M): no frames read")
    out.append(("wound dress (P28-A) [reading]: %s `wound` dressings sent (%s done) by part %s, part h first and last "
                "%s, %s `wound_held` lines (%s over WOUND_RESERVE, must read 0), parts undressed at the end %s; "
                "[inference] %s health fallen quiet on an undressed wound" % (
                    wd.get("sent"), wd.get("done"), wd.get("by_part"), wd.get("part_h"), wd.get("held"),
                    wd.get("held_over_reserve"), wd.get("parts_undressed_at_end"), wd.get("no_bleed_fall")))
               if wd.get("read") else "wound dress (P28-A): no decision log read")
    out.append(("shove back (P28-B2) [reading]: %s `shove_back` lines, %s legs; [inference] %s with a bite reaction "
                "during the leg, %s followed by a shove at the same zombie" % (
                    sb.get("lines"), sb.get("legs"), sb.get("bites_during"), sb.get("shoves_after")))
               if sb.get("read") else "shove back (P28-B2): no decision log read")
    out.append(("drift stand (P28-B3) [reading]: %s drifted pins' stance lines, %s legs; [inference] %s followed by a "
                "shove at the pin, %s by a bite reaction within BITE_AFTER_S" % (
                    ds.get("lines"), ds.get("legs"), ds.get("shoves_after"), ds.get("bites_after")))
               if ds.get("read") else "drift stand (P28-B3): no decision log read")
    out.append(("floor pain (P28-C) [reading]: %s floor swings at or over STRAIN_HARD, %s kills, %s older floor swings "
                "under the pain (must read 0); [inference] %s with a swing event, %s followed by a stomp at the same "
                "zombie" % (fp.get("swings"), fp.get("kills"), fp.get("swings_under_pain_before"), fp.get("landed"),
                            fp.get("stomps_after"))) if fp.get("read") else "floor pain (P28-C): no decision log read")
    out.append(("busy retry (P28-D) [reading]: %s `busy_retry` sends by kind %s; [inference] %s followed by a landed "
                "stomp at the same zombie, %s by its kill" % (
                    br.get("sends"), br.get("by_kind"), br.get("stomps_landed_after"), br.get("kills_after")))
               if br.get("read") else "busy retry (P28-D): no decision log read")
    out.append(("circle (P28-E) [reading]: %s circle legs by side %s, %s off CIRCLE_TURN (must read 0); [inference] "
                "%s sides switched, %s straight `back` legs at two or more standing within KEEP_R" % (
                    ci.get("legs"), ci.get("sides"), ci.get("off_turn"), ci.get("blocked_turns"),
                    ci.get("straight_two"))) if ci.get("read") else "circle (P28-E): no decision log read")
    so, st = E._d(fa.get("shoves_off")), E._d(fa.get("stomps_off"))
    out.append(("facing (P28-F) [reading]: %s attack swings by the points off the target %s (%s unread), shoves %s "
                "(%s unread), stomps %s (%s unread); [inference] each swing event the last accepted act's" % (
                    fa.get("swings"), fa.get("off_by_points"), fa.get("unread"), so.get("off_by_points"),
                    so.get("unread"), st.get("off_by_points"), st.get("unread")))
               if fa.get("read") else "facing (P28-F): no decision log read")
    out.append(("client end (the spec's 1 (c)) [reading]: the stop %s, loop.end seq %s health %s" % (
                    ce.get("stopped"), ce.get("seq"), ce.get("health")))
               if ce.get("read") else "client end (the spec's 1 (c)): no decision log read")
    return out


def report_lines_e18(g):
    """report_lines_e17's lines (the gate line naming gate_e18) then one line per pass 18 reading (`lines_e18`)."""
    g = E._d(g)
    out = [("gate_e18 " + ln[len("gate_e17 "):]) if ln.startswith("gate_e17 ") else ln
           for ln in G17.report_lines_e17(g)]
    return out + lines_e18(g)


def grade_e18(out, prev=None, decision_lines=None, state_dir=None, lines=None):
    """grade_e17 under "grade_e18" with the nine readings of pass 18 (`NEW`, `readings_e18`; `hits` off the frames,
    every other {"read": False} without a decision log; they read the state lines' act lines, events and frames)."""
    out = E._d(out)
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    g = G17.grade_e17(out, prev, decision_lines, state_dir, lines=lines)
    g["grade"] = "grade_e18"
    if files and "frames_files" in g:
        g["frames_files"] = files
    g.update(readings_e18(out, decision_lines, lines, E._d(g.get("kills")).get("planner")))
    g["report_lines"] = report_lines_e18(g)
    return g


def gate_e18(outs):
    """gate_e13 (neither grade_e14 to grade_e17 nor grade_e18 changes what it reads), named gate_e18."""
    return G17.gate_e17(outs)
