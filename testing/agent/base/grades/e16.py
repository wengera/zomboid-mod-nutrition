"""grades.e16 -- the chain sessions' grade, pass 16 (Plan 27 Task 2): `grade_e16` is `grades.e15.grade_e15` under
"grade_e16" with the nine readings of survival iteration 19 (Plan 27 Task 1, `T9_SWITCHES`), each read off the
decision log's why fields, the artifact's actions and the state log's act lines and frames:

  flee_finish     P27-A, the finish under a flee (`FLEE_FINISH`): the finishes sent by the flee's reason, their kills,
                  the struck and the unstruck, the refused.
  many_tail       P27-B, the `many` episode's tail (`MANY_TAIL`): the ends, the lone fights after them, the re-entries.
  hold_fight      P27-C, the hold's lone zombie (`HOLD_LONE`): the `hold_fight` lines, their shoves, stomps and kills.
  hold_rest       P27-C2, the hold's rest (`HOLD_REST`): the `rest` ticks and the endurance's rise per game minute
                  standing, against the endurance hold's walk with no zombie within DANGER_R (E18's, the comparison).
  spent_kept      P27-D, the spent dressing kept on a long bleed (`SPENT_KEEP`): the `spent_kept` lines, their parts
                  and the health across them.
  low_swing       P27-E, the low fight's swing (`LOW_SWING`): the swings sent, landed, the target's health across each.
  wounded_swings  P26-L1's swings read (spec section 2 (g), no switch): the `wounded_swing` swings sent, landed, the
                  target's health across each and the frames after each reading a new wound on the player.
  window_still    the WINDOW_STALL_S margin per climb: each window act's accept-to-done and still seconds.
  unwear_live     P26-O's first live reading: the unwears sent, done, refused by reason and the rip after a done one.

Each reading is {"read": False} without a decision log. A key marked reading counts what the log or the artifact
states; one marked inference reads an effect off the frames or the order of lines. Every live planner name the
readings read is copied below as a frozen constant with its source and its value at e743d150 (ruling P26-Q,
`grades/__init__.py`): this module imports nothing from `agent.base.planner` or `agent.base.world`; the chain it
imports (`grades.e15.grade_e15`, which reads live names through `e14` and `gates_e`) is pinned by the regrade tests of
the artifacts graded through it. Frozen once an artifact carries its output; `gates_e`, `grades/e14.py`,
`grades/e15.py` and every driver stay untouched."""
import bisect
import math

from agent.base import gates_e as E
from agent.base.grades import e14 as G14
from agent.base.grades import e15 as G15

# Frozen copies of the live planner names read here (P26-Q), each as it stood at e743d150 (Plan 27 Task 1's head).
DANGER_R = 6.0                 # planner/policies.py:74: tiles, a zombie this close is a threat
FINISH_CLEAR_R = 3.0           # planner/policies.py:276: tiles, a flee's finish goes with no standing zombie this near
MANY_TAIL_TICKS = 4            # planner/policies.py:281: strung-out ticks that end a `many` episode
SPENT_REDRESS_BT = 10.0        # planner/policies.py:286: a spent dressing not bleeding is replaced at this bleedingTime
                               # or under
SHOVE_FAIL_N = 3               # planner/policies.py:268: missed shoves at a lone target before the low fight's swing
WINDOW_STALL_S = 3.0           # planner/policies.py:115: wall seconds a window act may leave the player still before
                               # the Flee drops it
FLEE_FINISH_REASONS = ("strain", "pair", "many")    # planner/finish.py:18: the flee reasons whose episode finishes

TAIL_AFTER_LINES = 20          # log lines: a `many` tail's end is read this far on for its lone fight and a re-entry
                               # (ten seconds at the drivers' PLANNER_HZ 2)
WOUND_AFTER_S = 5.0            # wall seconds: a swing's wound frames are read from its send to this long after its end
REFUSED = ("failed", "rejected")
SWINGS = ("stomp", "attack")
NEW = ("flee_finish", "many_tail", "hold_fight", "hold_rest", "spent_kept", "low_swing", "wounded_swings",
       "window_still", "unwear_live")


def _world_min(f0, f1):
    """Game minutes from frame `f0` to `f1`: `World.world_minutes`' clock copied (world.py:541 at e743d150), the
    frames' `worldAge * 60` when both carry it, else their gameMin difference with one midnight wrap added when
    negative; None when neither reads."""
    a0, a1 = E._n(E._d(f0).get("worldAge")), E._n(E._d(f1).get("worldAge"))
    if a0 is not None and a1 is not None:
        return round(a1 * 60.0, 6) - round(a0 * 60.0, 6)
    g0, g1 = E._n(E._d(f0).get("gameMin")), E._n(E._d(f1).get("gameMin"))
    if g0 is None or g1 is None:
        return None
    return g1 - g0 if g1 >= g0 else g1 - g0 + 1440.0


def _square(f):
    """(x, y, z) of the frame's player square, floored as `gates_e._outside` floors it; None without a position."""
    me = E._d(E._d(f).get("me"))
    x, y = E._n(me.get("x")), E._n(me.get("y"))
    return None if x is None or y is None else (int(math.floor(x)), int(math.floor(y)), int(E._n(me.get("z")) or 0))


def _zhealth(f, zid):
    """The health the frame lists for zombie `zid`, else None (not listed, or no health read)."""
    for z in E._l(E._d(f).get("zombies")):
        if isinstance(z, dict) and z.get("id") == zid:
            return E._n(z.get("health"))
    return None


def _target_health(L, ln, acts):
    """[before, after] of the swing's target's health (an inference off the frames): `before` the frame at the line's,
    `after` the first frame after the swing's end (its terminal act line, else the row's endedS) that lists it; None
    where no frame lists it."""
    zid = E._d(E._d(ln.get("action")).get("args")).get("targetId")
    f0, row = L.frame(ln), L.action(ln)
    before = _zhealth(f0, zid) if f0 is not None else None
    end_ms = G14._end_ms(L, row, acts) if row is not None else None
    walls, frames = L.index
    lo = bisect.bisect_right(walls, end_ms if end_ms is not None else (E._n(ln.get("wall")) or 0.0) * 1000.0)
    after = next((h for h in (_zhealth(f, zid) for f in frames[lo:]) if h is not None), None)
    return [before, after]


def _swing_lines(L, key):
    """The threat lines whose why carries `key` (not None) and those of them that sent an `attack`."""
    rows = [ln for ln in L.rows if ln.get("branch") == "threat" and L.why(ln).get(key) is not None]
    return rows, [ln for ln in rows if E._sent(ln, "attack")]


def e_flee_finish(L):
    """The finish under a flee (P27-A, `Threat.FLEE_FINISH`): {read, lines, sent, kills, landed, struck, unstruck,
    refused, clear_within}. Reading: `lines` the threat lines whose why carries `flee_finish` {reason, struck, clear}
    (`finish.ThreatFinish._flee_finish`: the planner writes it only on the tick it sends the finish), `sent` those that
    sent a stomp or a floor strike by the flee's `reason` (FLEE_FINISH_REASONS, any other "other"), `kills` the zombies
    their results read dead, `landed` the sends `gates_e._landed` reads, `struck` and `unstruck` the sends whose
    `struck` reads true (the target struck within UNREACHABLE_S, P24-AQ's old candidate) and not (the zombies P27-A's
    widening reached), `refused` the sends whose action ended failed or rejected for any reason but `superseded` (the
    flee's next leg). Inference off the planner's own reading: `clear_within` the sends whose `clear` (the nearest
    listed standing zombie's tiles) reads at or within FINISH_CLEAR_R (must read 0: the rule's own clearance)."""
    if L is None:
        return {"read": False}
    lines, sent, by = 0, [], {}
    struck = refused = landed = within = 0
    for ln in L.rows:
        ff = L.why(ln).get("flee_finish")
        if ln.get("branch") != "threat" or not isinstance(ff, dict):
            continue
        lines += 1
        if not any(E._sent(ln, k) for k in SWINGS):
            continue
        sent.append(ln)
        G14._inc(by, ff.get("reason") if ff.get("reason") in FLEE_FINISH_REASONS else "other")
        struck += 1 if ff.get("struck") is True else 0
        landed += 1 if E._landed(L, ln) else 0
        c = E._n(ff.get("clear"))
        within += 1 if c is not None and c <= FINISH_CLEAR_R else 0
        row = L.action(ln)
        refused += 1 if row is not None and row.get("state") in REFUSED and row.get("reason") != "superseded" else 0
    return {"read": True, "lines": lines, "sent": by, "kills": len(L.kill_ids(sent)), "landed": landed,
            "struck": struck, "unstruck": len(sent) - struck, "refused": refused, "clear_within": within}


def e_many_tail(L):
    """The `many` episode's tail (P27-B, `Threat.MANY_TAIL`): {read, ends, lone_fights_after, kills_after, re_entries,
    short, crowded}. Reading: `ends` the lines whose threat why carries `many_tail` {ticks, standing, pressing}
    (`Threat._many_tail_read`, logged on the tick the tail ended the episode), `short` those whose `ticks` read under
    MANY_TAIL_TICKS and `crowded` those whose `standing` or `pressing` read over 1 (both must read 0: the rule's own
    condition). Inference off the order of lines: `lone_fights_after` the ends after which a threat fight line
    (`fight` true) came, on the end's own line or within TAIL_AFTER_LINES after it, before any line fleeing `many`;
    `kills_after` the zombies those fight lines killed; `re_entries` the ends after which a line fleeing `many` came
    within TAIL_AFTER_LINES (a new episode)."""
    if L is None:
        return {"read": False}
    rows = L.rows
    ends = lone = again = short = crowded = 0
    kills = []
    for i, ln in enumerate(rows):
        mt = L.why(ln).get("many_tail")
        if not isinstance(mt, dict):
            continue
        ends += 1
        t, s, p = (E._n(mt.get(k)) for k in ("ticks", "standing", "pressing"))
        short += 1 if t is not None and t < MANY_TAIL_TICKS else 0
        crowded += 1 if (s is not None and s > 1) or (p is not None and p > 1) else 0
        fights, back = [], False
        for j in range(i, min(len(rows), i + 1 + TAIL_AFTER_LINES)):
            if j > i and L.why(rows[j]).get("flee") == "many":
                back = True
                break
            if L.is_fight(rows[j]):
                fights.append(rows[j])
        lone += 1 if fights else 0
        again += 1 if back else 0
        kills += [k for k in L.kill_ids(fights) if k not in kills]
    return {"read": True, "ends": ends, "lone_fights_after": lone, "kills_after": len(kills), "re_entries": again,
            "short": short, "crowded": crowded}


def e_hold_fight(L):
    """The hold's lone zombie (P27-C, `Threat.HOLD_LONE`): {read, lines, runs, shoves, stomps, attacks, kills}. Reading:
    `lines` the threat lines whose why reads `hold_fight` true (`threat.SHOVE_ONLY_WHY`'s "hold": the endurance hold's
    shove-and-stomp Fight), `runs` the runs of adjacent ones, `shoves`, `stomps` and `attacks` the sends of each kind on
    them (`attacks` must read 0: the hold fight takes no swing) and `kills` the zombies their results read dead."""
    if L is None:
        return {"read": False}
    lines, runs, prev = [], 0, False
    for ln in L.rows:
        on = ln.get("branch") == "threat" and L.why(ln).get("hold_fight") is True
        if on:
            lines.append(ln)
            runs += 0 if prev else 1
        prev = on
    return {"read": True, "lines": len(lines), "runs": runs, "shoves": E._sent_count(lines, "shove"),
            "stomps": E._sent_count(lines, "stomp"), "attacks": E._sent_count(lines, "attack"),
            "kills": len(L.kill_ids(lines))}


def _clear(ln):
    """No zombie within DANGER_R at the line: its `inputs.threats` (the planner's own count) at 0, else its
    `inputs.nearest` absent or beyond DANGER_R."""
    inp = E._d(ln.get("inputs"))
    t = E._n(inp.get("threats"))
    if t is not None:
        return t == 0
    d = E._n(inp.get("nearest"))
    return d is None or d > DANGER_R


def _walk_line(L, ln):
    """An endurance hold's walk with no zombie within DANGER_R (P25-C's walk, E18's): a threat line fleeing `strain`
    whose `strain` kind reads `endurance`, `hold_walk` true and `_clear`."""
    w = L.why(ln)
    st = w.get("strain")
    return (ln.get("branch") == "threat" and w.get("flee") == "strain" and isinstance(st, dict)
            and st.get("kind") == "endurance" and w.get("hold_walk") is True and _clear(ln))


def _rise(L, idx):
    """The endurance's rise per game minute over the adjacent pairs of the line indexes `idx` (an inference off the
    frames): each pair's `stats.endurance` and game-minute differences (`_world_min`) between the frames at its two
    lines, summed; {read, frames, pairs, minutes, rise, rise_per_min}, {"read": False} with fewer than two frames or
    no game minute passed."""
    de = dm = 0.0
    pairs, seen = 0, set()
    for a, b in zip(idx, idx[1:]):
        if b != a + 1:
            continue
        f0, f1 = L.frame(L.rows[a]), L.frame(L.rows[b])
        if f0 is None or f1 is None or f0 is f1:
            continue
        e0, e1 = (E._n(E._d(E._d(f).get("stats")).get("endurance")) for f in (f0, f1))
        m = _world_min(f0, f1)
        if e0 is None or e1 is None or m is None:
            continue
        de, dm, pairs = de + (e1 - e0), dm + m, pairs + 1
        seen |= {id(f0), id(f1)}
    if len(seen) < 2 or dm <= 0:
        return {"read": False}
    return {"read": True, "frames": len(seen), "pairs": pairs, "minutes": dm, "rise": de, "rise_per_min": de / dm}


def e_hold_rest(L):
    """The hold's rest (P27-C2, `Threat.HOLD_REST`): {read, ticks, near, walk_ticks, standing, walking}. Reading:
    `ticks` the lines whose threat why carries `rest` {endurance, since_min} (`Threat._rest`, whatever branch answered:
    the rest sends nothing) and `near` those with a zombie within DANGER_R (`_clear` false; must read 0); `walk_ticks`
    the comparison's lines (`_walk_line`: the endurance hold's walk with no zombie within DANGER_R, E18's 158 walk
    lines among them). Inference off the frames: `standing` the endurance's rise per game minute between adjacent rest
    ticks, `walking` the same between adjacent walk ticks (`_rise`; each {"read": False} with fewer than two frames)."""
    if L is None:
        return {"read": False}
    rest = [i for i, ln in enumerate(L.rows) if isinstance(L.why(ln).get("rest"), dict)]
    walk = [i for i, ln in enumerate(L.rows) if _walk_line(L, ln)]
    return {"read": True, "ticks": len(rest), "near": sum(1 for i in rest if not _clear(L.rows[i])),
            "walk_ticks": len(walk), "standing": _rise(L, rest), "walking": _rise(L, walk)}


def e_spent_kept(L):
    """The spent dressing kept on a long bleed (P27-D, `Survive.SPENT_KEEP`): {read, lines, parts, health_across, short,
    redressed}. Reading: `lines` the lines whose care why carries `spent_kept` {part, bleedingTime, dirty}
    (`care.Care.choose`, logged where the spent step would have sent before it), `parts` them by part, `short` those
    whose `bleedingTime` reads at or under SPENT_REDRESS_BT (must read 0: the rule replaces there), `redressed` the
    care lines that sent a `bandage` for the `spent` reason (the replaces the rule still makes); `health_across` per
    part the health (`gates_e._line_health`: the planner's, else the frame's) at its first and its last kept line."""
    if L is None:
        return {"read": False}
    n = short = redressed = 0
    parts, across = {}, {}
    for ln in L.rows:
        c = E._bw(ln, "care")
        if ln.get("branch") == "care" and c.get("reason") == "spent" and E._sent(ln, "bandage"):
            redressed += 1
        k = c.get("spent_kept")
        if not isinstance(k, dict):
            continue
        n += 1
        p = str(k.get("part"))
        G14._inc(parts, p)
        h = E._line_health(L, ln)
        across.setdefault(p, [h, h])[1] = h
        bt = E._n(k.get("bleedingTime"))
        short += 1 if bt is not None and bt <= SPENT_REDRESS_BT else 0
    return {"read": True, "lines": n, "parts": parts, "health_across": across, "short": short,
            "redressed": redressed}


def e_low_swing(L, lines):
    """The low fight's swing (P27-E, `Threat.LOW_SWING`): {read, lines, sent, landed, health_before_after, short}.
    Reading: `lines` the threat lines whose why carries `low_swing` {target, missed} (`shove.FightShove._low_swing`),
    `sent` those that sent the `attack`, `landed` the sends `gates_e._landed` reads, `short` the sends whose `missed`
    reads under SHOVE_FAIL_N (must read 0). Inference off the frames: `health_before_after` per send the target's
    health at the line and after the swing's end (`_target_health`)."""
    if L is None:
        return {"read": False}
    acts = G14._acts(lines, "attack")
    rows, sent = _swing_lines(L, "low_swing")
    short = sum(1 for ln in sent if (E._n(E._d(L.why(ln).get("low_swing")).get("missed")) or 0) < SHOVE_FAIL_N)
    return {"read": True, "lines": len(rows), "sent": len(sent), "landed": sum(1 for ln in sent if E._landed(L, ln)),
            "health_before_after": [_target_health(L, ln, acts) for ln in sent], "short": short}


def _wounds(f):
    """(scratched + bitten, the parts reading `bleeding` true) of a frame's body."""
    b = E._d(E._d(f).get("body"))
    n = (E._n(b.get("scratched")) or 0) + (E._n(b.get("bitten")) or 0)
    return n, {p.get("i") for p in E._l(b.get("parts")) if isinstance(p, dict) and p.get("bleeding") is True}


def _wound_frames(L, ln, row, acts):
    """The indexes (into `L.index`) of the frames from the swing's send to WOUND_AFTER_S after its end (`G14._end_ms`,
    else its send) that read a new wound against the frame at the line: more parts scratched or bitten, or a part
    bleeding that was not."""
    f0 = L.frame(ln)
    if f0 is None:
        return set()
    n0, bled0 = _wounds(f0)
    w = (E._n(ln.get("wall")) or 0.0) * 1000.0
    end = G14._end_ms(L, row, acts) if row is not None else None
    walls, frames = L.index
    lo = bisect.bisect_right(walls, w)
    hi = bisect.bisect_right(walls, (end if end is not None else w) + WOUND_AFTER_S * 1000.0)
    got = set()
    for i in range(lo, min(hi, len(frames))):
        n, bled = _wounds(frames[i])
        if n > n0 or bled - bled0:
            got.add(i)
    return got


def e_wounded_swings(L, lines):
    """P26-L1's swings read (spec section 2 (g)): {read, lines, sent, landed, health_before_after, wound_frames_after,
    wounded}. Reading: `lines` the threat lines whose why carries `wounded_swing` (the misses, `shove.FightShove`'s
    divided swing), `sent` those that sent the `attack`, `landed` the sends `gates_e._landed` reads. Inference off the
    frames: `health_before_after` per send the target's health at the line and after the swing's end
    (`_target_health`), `wound_frames_after` the distinct frames after the sends reading a new wound on the player
    (`_wound_frames`; the windows of swings sent a second apart overlap, so a frame counts once) and `wounded` the
    sends with one or more."""
    if L is None:
        return {"read": False}
    acts = G14._acts(lines, "attack")
    rows, sent = _swing_lines(L, "wounded_swing")
    found = [_wound_frames(L, ln, L.action(ln), acts) for ln in sent]
    return {"read": True, "lines": len(rows), "sent": len(sent), "landed": sum(1 for ln in sent if E._landed(L, ln)),
            "health_before_after": [_target_health(L, ln, acts) for ln in sent],
            "wound_frames_after": len(set().union(*found)), "wounded": sum(1 for c in found if c)}


def _still_s(L, acc, done):
    """The longest wall seconds between the accept `acc` (ms) and the act's end `done` (else the last frame) on which
    the player's square (`_square`) did not change: each run of frames on one square from its first frame (the first
    run from the accept) to the first frame on another square, the last run to the end; None when no frame there reads
    a square."""
    walls, frames = L.index
    lo = bisect.bisect_left(walls, acc)
    hi = bisect.bisect_right(walls, done) if done is not None else len(walls)
    sq0 = start = last = None
    best = 0.0
    for w, f in zip(walls[lo:hi], frames[lo:hi]):
        sq = _square(f)
        if sq is None:
            continue
        if sq0 is None:
            sq0, start = sq, acc
        elif sq != sq0:
            best = max(best, w - start)
            sq0, start = sq, w
        last = w
    if sq0 is None:
        return None
    return round(max(best, (done if done is not None else last) - start) / 1000.0, 3)


def e_window_still(L, lines):
    """The window climb's still time against WINDOW_STALL_S: {read, climbs [{aid, state, accept_done_s, still_s}],
    over}. Reading, off the state log's `window` act lines (every branch's): per act `accept_done_s` the wall seconds
    from its `accepted` line (else its first) to its terminal line (None while it runs) and `state` that line's state
    ("running" without one). Inference off the frames: `still_s` the seconds from the accept on which the player's
    square did not change (`_still_s`: the longest such run, the walk to the window apart) and `over` the climbs whose
    still time reads WINDOW_STALL_S or more (a climb the stall read would have dropped as it stood)."""
    if L is None:
        return {"read": False}
    by = {}
    for ln in E._l(lines):
        if isinstance(ln, dict) and ln.get("kind") == "act" and ln.get("type") == "window":
            by.setdefault(ln.get("aid"), []).append(ln)
    climbs = []
    for aid, rows in by.items():
        acc = next((E._n(r.get("wallMs")) for r in rows if r.get("state") == "accepted"), E._n(rows[0].get("wallMs")))
        end = next((r for r in rows if r.get("state") in G14.TERMINAL), None)
        done = E._n(end.get("wallMs")) if end is not None else None
        climbs.append({"aid": aid, "state": end.get("state") if end is not None else "running",
                       "accept_done_s": round((done - acc) / 1000.0, 3) if done is not None and acc is not None
                       else None,
                       "still_s": _still_s(L, acc, done) if acc is not None else None})
    return {"read": True, "climbs": climbs,
            "over": sum(1 for c in climbs if c["still_s"] is not None and c["still_s"] >= WINDOW_STALL_S)}


def e_unwear_live(out, L, lines):
    """The unwear's live reading (P26-O): {read, sent, done, rejected, failed, rip_after}. Reading, off loop.actions'
    `unwear` rows (every branch's; the terminal act line's state and reason where the state log carries one): `sent`
    them, `done` those that ended done, `rejected` and `failed` the others by reason, `rip_after` the done ones
    followed by a `rip` action of the same item sent at or after the unwear's end (the care's rip of the garment it
    took off)."""
    if L is None:
        return {"read": False}
    acts = G14._acts(lines, "unwear")
    rows, rips = G14._loop_actions(out, "unwear"), G14._loop_actions(out, "rip")
    done = rip_after = 0
    rejected, failed = {}, {}
    for a in rows:
        end = acts.get(a.get("aid"), (None, None))[1]
        state, reason = (end.get("state"), end.get("reason")) if end is not None else (a.get("state"), a.get("reason"))
        if state == "rejected":
            G14._inc(rejected, str(reason))
        elif state == "failed":
            G14._inc(failed, str(reason))
        if state != "done":
            continue
        done += 1
        iid = E._d(a.get("args")).get("itemId")
        t = E._n(a.get("endedS"))
        t = t if t is not None else (E._n(a.get("sentS")) or 0.0)
        rip_after += 1 if any(E._d(r.get("args")).get("itemId") == iid and (E._n(r.get("sentS")) or 0.0) >= t
                              for r in rips) else 0
    return {"read": True, "sent": len(rows), "done": done, "rejected": rejected, "failed": failed,
            "rip_after": rip_after}


def readings_e16(out, decision_lines, lines):
    """{key: reading} of the nine readings of survival iteration 19 (`NEW`), each {"read": False} without a decision
    log; `grades.f8.grade_f8` reads them too."""
    out = E._d(out)
    L = E._Lines(out, decision_lines, lines) if decision_lines is not None else None
    return {"flee_finish": e_flee_finish(L), "many_tail": e_many_tail(L), "hold_fight": e_hold_fight(L),
            "hold_rest": e_hold_rest(L), "spent_kept": e_spent_kept(L), "low_swing": e_low_swing(L, lines),
            "wounded_swings": e_wounded_swings(L, lines), "window_still": e_window_still(L, lines),
            "unwear_live": e_unwear_live(out, L, lines)}


def _rise_text(r):
    r = E._d(r)
    return ("%s a game minute over %s game minutes (%s frames, %s pairs)" % (
        r.get("rise_per_min"), r.get("minutes"), r.get("frames"), r.get("pairs")) if r.get("read")
        else "not read (fewer than two frames)")


def lines_e16(g):
    """One report line per pass 16 reading, each clause marked reading or inference (`grades.f8` appends them too)."""
    ff, mt, hf, hr, sk, ls, ws, wn, uw = (E._d(g.get(k)) for k in NEW)
    out = []
    out.append(("flee finish (P27-A) [reading]: %s lines, sent by reason %s, %s kills, %s landed, %s struck, %s "
                "unstruck, %s refused; [inference] %s sent with a standing zombie at or within FINISH_CLEAR_R (must "
                "read 0)" % (ff.get("lines"), ff.get("sent"), ff.get("kills"), ff.get("landed"), ff.get("struck"),
                             ff.get("unstruck"), ff.get("refused"), ff.get("clear_within")))
               if ff.get("read") else "flee finish (P27-A): no decision log read")
    out.append(("many tail (P27-B) [reading]: %s ends, %s short of MANY_TAIL_TICKS and %s crowded (both must read 0); "
                "[inference] %s followed by a fight (%s kills), %s by a new `many` episode within TAIL_AFTER_LINES" % (
                    mt.get("ends"), mt.get("short"), mt.get("crowded"), mt.get("lone_fights_after"),
                    mt.get("kills_after"), mt.get("re_entries"))) if mt.get("read")
               else "many tail (P27-B): no decision log read")
    out.append(("hold fight (P27-C) [reading]: %s `hold_fight` lines in %s runs, %s shoves, %s stomps, %s attacks "
                "(must read 0), %s kills" % (hf.get("lines"), hf.get("runs"), hf.get("shoves"), hf.get("stomps"),
                                       hf.get("attacks"), hf.get("kills"))) if hf.get("read")
               else "hold fight (P27-C): no decision log read")
    out.append(("hold rest (P27-C2) [reading]: %s rest ticks, %s with a zombie within DANGER_R (must read 0), %s "
                "endurance-hold walk ticks with none; [inference] the endurance's rise standing %s, walking %s" % (
                    hr.get("ticks"), hr.get("near"), hr.get("walk_ticks"), _rise_text(hr.get("standing")),
                    _rise_text(hr.get("walking")))) if hr.get("read") else "hold rest (P27-C2): no decision log read")
    out.append(("spent kept (P27-D) [reading]: %s `spent_kept` lines by part %s, %s at or under SPENT_REDRESS_BT (must "
                "read 0), %s spent dressings replaced; health across the kept lines by part %s" % (
                    sk.get("lines"), sk.get("parts"), sk.get("short"), sk.get("redressed"), sk.get("health_across")))
               if sk.get("read") else "spent kept (P27-D): no decision log read")
    out.append(("low swing (P27-E) [reading]: %s lines, %s swings sent, %s landed, %s under SHOVE_FAIL_N misses (must "
                "read 0); [inference] the target's health before and after %s" % (
                    ls.get("lines"), ls.get("sent"), ls.get("landed"), ls.get("short"),
                    ls.get("health_before_after"))) if ls.get("read") else "low swing (P27-E): no decision log read")
    out.append(("wounded swings (P26-L1) [reading]: %s lines, %s swings sent, %s landed; [inference] the target's "
                "health before and after %s, %s frames after them reading a new wound (%s swings)" % (
                    ws.get("lines"), ws.get("sent"), ws.get("landed"), ws.get("health_before_after"),
                    ws.get("wound_frames_after"), ws.get("wounded"))) if ws.get("read")
               else "wounded swings (P26-L1): no decision log read")
    out.append(("window still (WINDOW_STALL_S) [reading]: climbs (aid, state, accept to done s; [inference] still s) "
                "%s; %s still for WINDOW_STALL_S or more" % (
                    [(c.get("aid"), c.get("state"), c.get("accept_done_s"), c.get("still_s"))
                     for c in E._l(wn.get("climbs"))], wn.get("over"))) if wn.get("read")
               else "window still (WINDOW_STALL_S): no decision log read")
    out.append(("unwear live (P26-O) [reading]: %s unwears sent, %s done, rejected %s, failed %s, %s followed by the "
                "rip of the garment" % (uw.get("sent"), uw.get("done"), uw.get("rejected"), uw.get("failed"),
                                        uw.get("rip_after"))) if uw.get("read")
               else "unwear live (P26-O): no decision log read")
    return out


def report_lines_e16(g):
    """report_lines_e15's lines (the gate line naming gate_e16) then one line per pass 16 reading (`lines_e16`)."""
    g = E._d(g)
    out = [("gate_e16 " + ln[len("gate_e15 "):]) if ln.startswith("gate_e15 ") else ln
           for ln in G15.report_lines_e15(g)]
    return out + lines_e16(g)


def grade_e16(out, prev=None, decision_lines=None, state_dir=None, lines=None):
    """grade_e15 under "grade_e16" with the nine readings of survival iteration 19 (`NEW`, `readings_e16`; each
    {"read": False} without a decision log; they read the state lines' act lines and frames)."""
    out = E._d(out)
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    g = G15.grade_e15(out, prev, decision_lines, state_dir, lines=lines)
    g["grade"] = "grade_e16"
    if files and "frames_files" in g:
        g["frames_files"] = files
    g.update(readings_e16(out, decision_lines, lines))
    g["report_lines"] = report_lines_e16(g)
    return g


def gate_e16(outs):
    """gate_e13 (neither grade_e14, grade_e15 nor grade_e16 changes what it reads), named gate_e16."""
    return E.gate_e13(outs)
