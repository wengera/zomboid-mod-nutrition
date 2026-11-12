"""grades.x6 -- the engagement grade (Plan 36 Task 5c): `grade_x6` is `grades.x5.grade_x5` under "grade_x6", with
"grade_x5" in `base`, x5's own base ("grade_x4") in `base_x5`, and x5's nesting below it kept (`base_x4` "grade_x3",
`base_x3` "grade_x2", `base_x2` "grade_x1", `base_x1` grade_f12 for an LLM session, grade_e21 for a chain one; x5's
five readings and x4's nine kept at the top level), plus eight readings of the engagement (the spec
`docs/superpowers/specs/2026-11-11-plan-36-the-engagement-design.md` section 3.6), each over the sources clipped at the
loop's stop (`x1.clip`):

  cadence     the press leaves (`result.press` on the melee act lines, each once: `press_leaves`, the scorecard's key)
              ({read: False} with no leaf carrying `moving_back` or `air`, a run before PZA/1.15): `presses` the leaves;
              `moving_back`, `air` and `air_launch` {n, of, share} the leaves reading the key true over those carrying
              it (`air` the collision tick's, Task 2a's addendum: a swing that landed nothing with the target beyond
              the reach over the whole flight; `air_launch` the launch's prediction); `done` {back_presses,
              air_presses, swings} summed over the melees' `done` lines (a failed line's counts are not read);
              `retreats` [{aid, presses, back}] per retreat (a run of one melee's act lines whose work leaf reads
              `retreat` true; a leaf on the line after the run belongs to it, the scorecard's window): the leaves
              launched in it and those launched on the moving back step.
  steps       the work leaf's reasons ({read: False} with none): `step_for`, `shove_for` and `repin_for` counted as runs
              (a value standing on consecutive lines of one melee counts once: the heartbeat re-reads it), each key's
              listed values first (STEP_FOR, SHOVE_FOR, REPIN_FOR, zero-filled), then any other seen;
              `nan_heading` the lines whose work leaf reads it truthy; `pile` x5's `work.pile` {episodes, shoves,
              knockdowns} (`grades.x5.e_work`).
  engage_pull the decision lines carrying `engage_pull` on any branch's why ({read: False} with none; the key is
              not `pull`, x1's P24-AN reading): `lines`, and
              `by` {why: {lines, held (`held` true), closed (`room` "closed": no open heading, the vector dropped),
              clamped (`room` {from}: the heading moved to the ring's), episodes (a line whose previous decision line
              carried no pull of that why), spread_first_median (the median `spread` over the episodes' first lines,
              None without one)}}, PULL_WHYS first; `spread_first_median` over every episode.
  cone_bites  the reaction onsets (`x1.reaction_segments`' first frames: a type change inside a run an onset too)
              with a standing zombie listed and `me.bodyAngle` ({read: False} with no frame carrying `me.bodyAngle`):
              `bites` those read, `outside` those whose nearest standing zombie (by x, y off the onset frame) lies more
              than CONE_DEG off the body (|wrap(bodyAngle - atan2(zy - y, zx - x))|, radians, grades.x2's convention,
              T105's), `rows` [{seq, angle (degrees, signed), outside}]; the scorecard's `cone_bites` (tools/
              trial_score.py, Plan 36 Task 5b), copied.
  clock       the Task 4 clock's why (`clock {action, ttc, need[, waited][, running][, cut]}`) on any branch, each
              read once ({read: False} with none): `lines`; `allowed` (a line that sent: the scorecard's `ok`),
              `held` (no send), `cut` (`cut` true); `by_action` {action: {allowed, held, cut}}; `waited` the sum;
              `under` the allowed clocks with `ttc` strictly under `need` (an action started inside the margin: the
              criterion reads 0), `under_lines` their indices; the scorecard's `clock_gate`, copied, and beside it
              `steer_cuts` the care and loot actions (CARE_KINDS) ending `failed superseded` whose superseding send
              (the last sent decision line at or before the failed line, after the action's own send) is a steer (the
              criterion reads 0), `superseded_by` {type: n} over those actions; `durations` {kind: {n, median}} the
              timed actions' seconds (TIMED, `action_kind`), from the `accepted` line (else the send) to the `done`.
  crawler     ({read: False} without a frame) `frames` and `seconds` the frames with a living crawler within
              CRAWLER_R tiles while the act's step is in CRAWLER_STEPS at a standing target (the melee's latest
              `result.target` at or before the frame, else the nearest standing; the scorecard's `crawler_close`,
              copied); `buffer` the `crawler_buffer` step runs (the steps reading's).
  room        the frames carrying `me.room` ({read: False} with none): `frames`, `stops` {kind: n} over every heading
              of those frames, `ms_p50` and `ms_max` of `cost.roomMs` (the scorecard's `room_readings`, copied); and
              `bites` [{seq, closed, behind, behind_closed}] at each reaction run's onset (`e21._reaction_runs`' first
              frames): the ring the onset frame or one of the ROOM_EVERY - 1 frames before carried (the Sense's
              cadence), `closed` its headings reading under ROOM_NEED, `behind` its headings more than CONE_DEG off
              the body (`me.bodyAngle`; None without it), `behind_closed` those closed; a bite with no ring that near
              reads `closed` None; `bites_read` the onsets with a ring.
  rip_ride    the rips sent ({read: False} with no decision log): `riding` (args `keepMoving` true: the Tend side
              slot, Task 2b's 7c) and `standing` (the others), each {sent, done, failed, superseded, open} by the
              matched act line's end (`failed` any other failure or a rejection; `open` no end read).

A sent decision line and an act line are matched by type and wall: an aid's send is the latest unmatched sent line of
its type at or before the aid's first act line (`aid_sends`; the send precedes its first line by tens of ms on the
trial and on F21, every type's count equal).

Frozen once an artifact carries its output (`grades/__init__.py`): every live name it reads is copied below with its
source, and it imports nothing from `agent.base.planner`, `agent.base.world` or `tools`; the scorecard's readers are
copied (never imported: the scorecard is live). `grades.x5`, `grades.x2.wrap_deg`, `grades.x1` and the frozen
e-grades' readers (`e18._reaction`, `e21._reaction_runs`, as `grades.x1` imports them) and the shared readers of
`gates_e` are its only imports."""
import math
import statistics

from agent.base import gates_e as E
from agent.base.grades import e18 as G18
from agent.base.grades import e21 as G21
from agent.base.grades import x1 as GX1
from agent.base.grades import x2 as GX2
from agent.base.grades import x5 as GX5

# Frozen copies of the live names read here (P26-Q), each with its source.
MELEE = GX5.MELEE          # schema actionType (PZA/1.8), x5's copy
DONE = "done"              # the act line's state at a done end
FAILED = "failed"          # ... at a failed end
REJECTED = "rejected"      # ... at a rejection
ACCEPTED = "accepted"      # ... at the Lua's acceptance
SUPERSEDED = "superseded"  # the failed line's reason when the planner sent another act (schema reason enum)
PRESS = "press"            # the melee result's press leaf (PZA/1.10)
MOVING_BACK = "moving_back"   # pza1.json result_melee press leaf (PZA/1.15, Plan 36 Task 2a)
AIR = "air"                # ... the collision tick's air (Task 2a's addendum, PZAgent_StanceMelee.lua K.meleeAirAt)
AIR_LAUNCH = "air_launch"  # ... the launch's prediction (K.meleePressAir)
DONE_COUNTS = ("back_presses", "air_presses", "swings")   # pza1.json result_melee counts (PZA/1.15; swings PZA/1.10)
WORK = "work"              # the result's work leaf (PZA/1.13)
RETREAT = "retreat"        # ... its fighting-retreat flag (Plan 35 fix 6)
STEP_KEYS = ("step_for", "shove_for", "repin_for")   # tools/trial_score.py:979 STEP_KEYS (at 3f1e86b5), a copy
STEP_FOR = ("gap", "retreat", "pile", "pile_out", "stagger_in", "crawler_buffer")   # pza1.json work.step_for (2b)
SHOVE_FOR = ("knockdown",)                 # pza1.json work.shove_for (Plan 36 Task 2b)
REPIN_FOR = ("stall", "attacker")          # pza1.json work.repin_for (Plan 35 fix 7b; Plan 36 Task 2b)
STEP_VALUES = {"step_for": STEP_FOR, "shove_for": SHOVE_FOR, "repin_for": REPIN_FOR}
NAN_HEADING = "nan_heading"   # pza1.json work.nan_heading (Plan 36 Task 1 fix 1)
CRAWLER_BUFFER = "crawler_buffer"   # ... step_for's crawler buffer (PZAgent_StanceWork.lua crawlerTick)
ENGAGE_PULL = "engage_pull"   # planner/group.py's pull why (Plan 36 Task 3: {why, spread, n, heading[, flank][, held]
PULL_WHYS = ("spread", "retreat", "cone")   # [, room]}); tools/trial_score.py:939 PULL_LETTERS' keys (at 3f1e86b5)
ROOM_CLOSED = "closed"     # planner/group.py:374 (Task 3 fix 3): room "closed", the vector dropped
ROOM_FROM = "from"         # planner/group.py:378: room {from: <raw heading>}, the heading clamped
CONE_DEG = 90.0            # degrees: tools/trial_score.py:828 CONE_DEG (Plan 36 Task 5b, at 3f1e86b5), a copy
CLOCK = "clock"            # planner/clock.py's why key (Plan 36 Task 4)
TIMED = ("rip", "unwear", "bandage", "loot", "door", "scan")   # planner/clock.py:56 TIMED (at 3f1e86b5), a copy
CARE_KINDS = ("rip", "unwear", "bandage", "loot")   # the brief's "a care or loot act": TIMED less door and scan
STEER = "steer"            # schema actionType: the leg a care must never be cut by
CRAWLER_R = 1.0            # tiles: tools/trial_score.py:888 CRAWLER_R (at 3f1e86b5), a copy
CRAWLER_STEPS = ("swing", "shove", "stomp")   # tools/trial_score.py:889 CRAWLER_STEPS (at 3f1e86b5), a copy
ROOM_NEED = 1.0            # tiles: PZAgent_StanceWork.lua:863 K.WORK_ROOM_NEED (at 3f1e86b5): a heading this clear
ROOM_STEP_DEG = 45.0       # degrees: PZAgent_StanceWork.lua:858 K.WORK_ROOM_HEADINGS' step (0, 45, ..., 315)
ROOM_EVERY = 3             # frames: PZAgent_Sense.lua:1116 S.ROOM_EVERY (at 3f1e86b5): a ring every third frame
RIP = "rip"                # schema actionType
KEEP_MOVING = "keepMoving"   # pza1.json args_rip.keepMoving (Plan 36 Task 2b, 7c)
NEW = ("cadence", "steps", "engage_pull", "cone_bites", "clock", "crawler", "room", "rip_ride")
N_LINES = len(NEW)         # the report lines lines_x6 appends: one per NEW key


def action_kind(type_, args):
    """planner/clock.py:63 `action_kind` (at 3f1e86b5), copied: the clock's kind of a command by its type and args
    (a riding bandage none), else None."""
    if type_ in ("rip", "unwear", "scan"):
        return type_
    if type_ == "bandage":
        return None if args.get("keepMoving") is True else "bandage"
    if type_ == "interact":
        k = args.get("kind")
        return "loot" if k == "loot" else ("door" if k in ("open", "close") else None)
    return None


# ---------------------------------------------------------------- shared readers
def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _median(vals):
    return statistics.median(vals) if vals else None


def _share(n, of):
    return {"n": n, "of": of, "share": (n / float(of)) if of else None}


def _ordered(seen, order):
    """{key: count} of the dict `seen`, the keys of `order` first (zero-filled), then the others in first-seen order."""
    out = {k: seen.get(k, 0) for k in order}
    out.update((k, n) for k, n in seen.items() if k not in out)
    return out


def branch_whys(r, key):
    """The dict values held under `key` on the decision line `r`'s branch whys (`inputs.branches`), in branch order."""
    out = []
    for w in E._d(E._d(r.get("inputs")).get("branches")).values():
        v = E._d(w).get(key)
        if isinstance(v, dict):
            out.append(v)
    return out


def act_by_aid(lines):
    """{aid: [act line]} of every act line, in log order, the aids in first-seen order."""
    by = {}
    for ln in E._l(lines):
        if isinstance(ln, dict) and ln.get("kind") == "act":
            by.setdefault(ln.get("aid"), []).append(ln)
    return by


def sends(rows):
    """[(wall_ms, type, args, index)] of the decision lines that sent an action (`sent` true), in log order."""
    out = []
    for i, r in enumerate(E._l(rows)):
        a = E._d(r.get("action"))
        w = E._n(r.get("wall"))
        if r.get("sent") is True and a.get("type") and w is not None:
            out.append((w * 1000.0, a.get("type"), E._d(a.get("args")), i))
    return out


def aid_sends(rows, lines):
    """{aid: send} (a `sends` tuple): each aid's send is the latest sent line of its type at or before the aid's first
    act line, past the send last matched to that type (the matches move forward in time); an aid with none is left
    out (the session's opening equip, a Lua-side stop)."""
    by_type = {}
    for s in sends(rows):
        by_type.setdefault(s[1], []).append(s)
    firsts = sorted(((E._n(lns[0].get("wallMs")), aid, lns[0].get("type")) for aid, lns in act_by_aid(lines).items()
                     if E._n(lns[0].get("wallMs")) is not None), key=lambda t: t[0])
    used, out = {}, {}
    for w, aid, typ in firsts:
        cand = by_type.get(typ, [])
        j = used.get(typ, -1)
        k = j
        while k + 1 < len(cand) and cand[k + 1][0] <= w:
            k += 1
        if k > j:
            out[aid] = cand[k]
            used[typ] = k
    return out


def end_line(lns):
    """The act's terminal line (done, failed or rejected), else None."""
    return next((ln for ln in lns if ln.get("state") in (DONE, FAILED, REJECTED)), None)


def press_leaves(lines):
    """tools/trial_score.py `press_leaves` (Plan 36 Task 5b, at 3f1e86b5), copied: [{aid, leaf, retreat, line}] of the
    melee press leaves, each once (keyed by its melee and its launch's `d_press`, `hp0` and `d_collide_pred`, a leaf
    with none by its line's `seq`), `retreat` true when its line or the melee's act line before it reads work
    `retreat` true; `line` (added here) the index of the leaf's first line in the melee's lines."""
    out, seen = [], set()
    for aid, lns in GX5.melee_lines(lines).items():
        prev = False
        for i, ln in enumerate(lns):
            res = E._d(ln.get("result"))
            own = bool(E._d(res.get(WORK)).get(RETREAT))
            leaf = res.get(PRESS)
            if isinstance(leaf, dict):
                key = (aid, leaf.get("d_press"), leaf.get("hp0"), leaf.get("d_collide_pred"))
                if key[1:] == (None, None, None):
                    key = (aid, ln.get("seq"))
                if key not in seen:
                    seen.add(key)
                    out.append({"aid": aid, "leaf": leaf, "retreat": own or prev, "line": i})
            prev = own
    return out


# ---------------------------------------------------------------- the readings
def e_cadence(lines):
    """The cadence reading (the module docstring)."""
    ls = press_leaves(lines)
    if not any(p["leaf"].get(MOVING_BACK) is not None or p["leaf"].get(AIR) is not None for p in ls):
        return {"read": False}

    def share(key):
        has = [p for p in ls if p["leaf"].get(key) is not None]
        return _share(sum(1 for p in has if p["leaf"].get(key) is True), len(has))

    done = {k: 0 for k in DONE_COUNTS}
    retreats = []
    by_line = {}
    for p in ls:
        by_line.setdefault((p["aid"], p["line"]), []).append(p)
    for aid, lns in GX5.melee_lines(lines).items():
        prev, cur = False, None
        for i, ln in enumerate(lns):
            res = E._d(ln.get("result"))
            if ln.get("state") == DONE:
                for k in DONE_COUNTS:
                    done[k] += _num(res.get(k)) or 0
            own = bool(E._d(res.get(WORK)).get(RETREAT))
            if own and not prev:
                cur = {"aid": aid, "presses": 0, "back": 0}
                retreats.append(cur)
            if (own or prev) and cur is not None:
                for p in by_line.get((aid, i), []):
                    cur["presses"] += 1
                    cur["back"] += 1 if p["leaf"].get(MOVING_BACK) is True else 0
            prev = own
    return {"read": True, "presses": len(ls), "moving_back": share(MOVING_BACK), "air": share(AIR),
            "air_launch": share(AIR_LAUNCH), "done": done, "retreats": retreats}


def e_steps(lines):
    """The steps reading (the module docstring): tools/trial_score.py `step_reasons` (at 3f1e86b5), copied, with each
    key's listed values first and x5's pile."""
    by, nan = {}, 0
    for lns in GX5.melee_lines(lines).values():
        prev = {}
        for ln in lns:
            w = E._d(E._d(ln.get("result")).get(WORK))
            for k in STEP_KEYS:
                v = w.get(k)
                if v is not None and v != prev.get(k):
                    by.setdefault(k, {})
                    by[k][str(v)] = by[k].get(str(v), 0) + 1
                prev[k] = v
            if w.get(NAN_HEADING):
                nan += 1
    if not by and not nan:
        return {"read": False}
    out = {k: _ordered(by.get(k, {}), STEP_VALUES[k]) for k in STEP_KEYS}
    work = GX5.e_work(lines)
    out.update(read=True, nan_heading=nan, pile=work.get("pile") if work.get("read") else None)
    return out


def e_pull(rows):
    """The pull reading (the module docstring)."""
    if rows is None:
        return {"read": False}
    by, firsts, n, prev = {}, [], 0, set()
    for r in E._l(rows):
        ps = branch_whys(r, ENGAGE_PULL)
        if ps:
            n += 1
        now = set()
        for p in ps:
            k = str(p.get("why"))
            now.add(k)
            b = by.setdefault(k, {"lines": 0, "held": 0, "closed": 0, "clamped": 0, "episodes": 0, "_first": []})
            b["lines"] += 1
            b["held"] += 1 if p.get("held") is True else 0
            room = p.get("room")
            b["closed"] += 1 if room == ROOM_CLOSED else 0
            b["clamped"] += 1 if isinstance(room, dict) and ROOM_FROM in room else 0
            if k not in prev:
                b["episodes"] += 1
                s = _num(p.get("spread"))
                if s is not None:
                    b["_first"].append(s)
                    firsts.append(s)
        prev = now
    if not n:
        return {"read": False}
    out = {}
    for k in list(PULL_WHYS) + [k for k in by if k not in PULL_WHYS]:
        if k in by:
            b = by[k]
            out[k] = {"lines": b["lines"], "held": b["held"], "closed": b["closed"], "clamped": b["clamped"],
                      "episodes": b["episodes"], "spread_first_median": _median(b["_first"])}
    return {"read": True, "lines": n, "by": out, "spread_first_median": _median(firsts)}


def _standing(z):
    """tools/trial_score.py `_standing` (x5's `standing_z`), copied."""
    return GX5.standing_z(z)


def _nearest_standing_xy(f):
    """(zombie, px, py) of the frame's nearest standing zombie by x, y off `me`'s x, y, else (None, px, py)."""
    me = E._d(f.get("me"))
    px, py = E._n(me.get("x")), E._n(me.get("y"))
    if px is None or py is None:
        return None, px, py
    zs = [(math.hypot(E._n(z.get("x")) - px, E._n(z.get("y")) - py), z) for z in (E._d(q) for q in
                                                                                 E._l(f.get("zombies")))
          if _standing(z) and E._n(z.get("x")) is not None and E._n(z.get("y")) is not None]
    return (min(zs, key=lambda t: t[0])[1] if zs else None), px, py


def e_cone_bites(frames):
    """The cone_bites reading (the module docstring): tools/trial_score.py `cone_bites` (at 3f1e86b5), copied, with
    each onset's row."""
    if not any(E._n(E._d(f.get("me")).get("bodyAngle")) is not None for f in frames):
        return {"read": False}
    rows = []
    for a, _ in GX1.reaction_segments(frames):
        f = frames[a]
        body = E._n(E._d(f.get("me")).get("bodyAngle"))
        z, px, py = _nearest_standing_xy(f)
        if body is None or z is None:
            continue
        ang = GX2.wrap_deg(body - math.atan2(E._n(z.get("y")) - py, E._n(z.get("x")) - px))
        rows.append({"seq": f.get("seq"), "angle": ang, "outside": abs(ang) > CONE_DEG})
    return {"read": True, "bites": len(rows), "outside": sum(1 for r in rows if r["outside"]), "rows": rows}


def e_clock(rows, lines):
    """The clock reading (the module docstring): tools/trial_score.py `clock_gate` (at 3f1e86b5), copied, by action,
    with the steer cuts and the durations."""
    if rows is None:
        return {"read": False}
    n = ok = held = cut = under = 0
    waited, idx, by = 0.0, [], {}
    for i, r in enumerate(E._l(rows)):
        for c in branch_whys(r, CLOCK):
            n += 1
            waited += E._n(c.get("waited")) or 0.0
            a = by.setdefault(str(c.get("action")), {"allowed": 0, "held": 0, "cut": 0})
            if c.get("cut"):
                cut += 1
                a["cut"] += 1
            elif r.get("sent") is True:
                ok += 1
                a["allowed"] += 1
                ttc, need = E._n(c.get("ttc")), E._n(c.get("need"))
                if ttc is not None and need is not None and ttc < need:
                    under += 1
                    idx.append(i)
            else:
                held += 1
                a["held"] += 1
    if not n:
        return {"read": False}
    acts, matched, sent = act_by_aid(lines), aid_sends(rows, lines), sends(rows)
    steer, by_type, durs = 0, {}, {}
    for aid, lns in acts.items():
        s = matched.get(aid)
        if s is None:
            continue
        kind = action_kind(s[1], s[2])
        end = end_line(lns)
        if kind is None or end is None:
            continue
        w_end = E._n(end.get("wallMs"))
        if end.get("state") == DONE and w_end is not None:
            acc = next((E._n(ln.get("wallMs")) for ln in lns if ln.get("state") == ACCEPTED), None)
            start = acc if acc is not None else s[0]
            durs.setdefault(kind, []).append((w_end - start) / 1000.0)
        if kind in CARE_KINDS and end.get("state") == FAILED and end.get("reason") == SUPERSEDED and w_end is not None:
            later = [t for t in sent if s[3] < t[3] and t[0] <= w_end]
            typ = later[-1][1] if later else None
            by_type[str(typ)] = by_type.get(str(typ), 0) + 1
            steer += 1 if typ == STEER else 0
    durations = {k: {"n": len(durs[k]), "median": _median(durs[k])} for k in TIMED if k in durs}
    return {"read": True, "lines": n, "allowed": ok, "held": held, "cut": cut, "by_action": by, "waited": waited,
            "under": under, "under_lines": idx, "steer_cuts": steer, "superseded_by": by_type,
            "durations": durations}


def e_crawler(frames, lines, steps):
    """The crawler reading (the module docstring): tools/trial_score.py `crawler_close` (at 3f1e86b5), copied, with
    the buffer steps."""
    if not frames:
        return {"read": False}
    tgt = {}
    for aid, lns in GX5.melee_lines(lines).items():
        tgt[aid] = [(E._n(ln.get("wallMs")), E._d(ln.get("result"))["target"]) for ln in lns
                    if E._d(ln.get("result")).get("target") is not None and E._n(ln.get("wallMs")) is not None]
    _, dur = GX5.frame_seconds(frames)
    n, secs = 0, 0.0
    for f, d in zip(frames, dur):
        act = E._d(f.get("act"))
        if act.get("step") not in CRAWLER_STEPS:
            continue
        zs = [E._d(z) for z in E._l(f.get("zombies"))]
        crawlers = [z for z in zs if z.get("crawler") and (E._n(z.get("health")) is None or E._n(z.get("health")) > 0)
                    and E._n(z.get("dist")) is not None and E._n(z.get("dist")) < CRAWLER_R]
        if not crawlers:
            continue
        w = E._n(f.get("wallMs"))
        known = [t for tw, t in tgt.get(act.get("aid"), []) if w is not None and tw <= w]
        target = next((z for z in zs if known and z.get("id") == known[-1]), None)
        if target is None:
            std = [z for z in zs if _standing(z) and E._n(z.get("dist")) is not None]
            target = min(std, key=lambda z: E._n(z.get("dist"))) if std else None
        if target is not None and _standing(target):
            n += 1
            secs += d
    buf = E._d(steps.get("step_for")).get(CRAWLER_BUFFER, 0) if steps.get("read") else 0
    return {"read": True, "frames": n, "seconds": secs, "buffer": buf}


def _ring(f):
    room = E._d(f.get("me")).get("room")
    return room if isinstance(room, dict) else None


def e_room(frames):
    """The room reading (the module docstring): tools/trial_score.py `room_readings` (at 3f1e86b5), copied, with the
    ring at each reaction run's onset."""
    stops, ms, n = {}, [], 0
    for f in frames:
        room = _ring(f)
        if room is None:
            continue
        n += 1
        for k in E._l(room.get("stop")):
            stops[k] = stops.get(k, 0) + 1
        v = E._n(E._d(f.get("cost")).get("roomMs"))
        if v is not None:
            ms.append(v)
    if not n:
        return {"read": False}
    bites = []
    for a, _ in G21._reaction_runs(frames):
        f = frames[a]
        ring = next((_ring(frames[i]) for i in range(a, max(a - ROOM_EVERY, -1), -1) if _ring(frames[i]) is not None),
                    None)
        row = {"seq": f.get("seq"), "closed": None, "behind": None, "behind_closed": None}
        if ring is not None:
            h = [_num(v) for v in E._l(ring.get("h"))]
            row["closed"] = sum(1 for v in h if v is not None and v < ROOM_NEED)
            body = E._n(E._d(f.get("me")).get("bodyAngle"))
            if body is not None:
                back = [i for i in range(len(h))
                        if abs(GX2.wrap_deg(math.radians(ROOM_STEP_DEG * i) - body)) > CONE_DEG]
                row["behind"] = len(back)
                row["behind_closed"] = sum(1 for i in back if h[i] is not None and h[i] < ROOM_NEED)
        bites.append(row)
    return {"read": True, "frames": n, "stops": stops, "ms_p50": _median(ms), "ms_max": max(ms) if ms else None,
            "bites": bites, "bites_read": sum(1 for b in bites if b["closed"] is not None)}


def e_rip_ride(rows, lines):
    """The rip_ride reading (the module docstring)."""
    if rows is None:
        return {"read": False}
    acts, matched = act_by_aid(lines), aid_sends(rows, lines)
    ends = {}
    for aid, s in matched.items():
        if s[1] == RIP:
            ends[s[3]] = end_line(acts.get(aid, []))
    out = {k: {"sent": 0, "done": 0, "failed": 0, "superseded": 0, "open": 0} for k in ("riding", "standing")}
    for w, typ, args, i in sends(rows):
        if typ != RIP:
            continue
        b = out["riding" if args.get(KEEP_MOVING) is True else "standing"]
        b["sent"] += 1
        end = ends.get(i)
        if end is None:
            b["open"] += 1
        elif end.get("state") == DONE:
            b["done"] += 1
        elif end.get("state") == FAILED and end.get("reason") == SUPERSEDED:
            b["superseded"] += 1
        else:
            b["failed"] += 1
    return dict(out, read=True)


def readings_x6(out, decision_lines, lines):
    """{key: reading} of the new keys (`NEW`: none an earlier grade's key, the pull `engage_pull` since x1's `pull` is
    P24-AN's), over the sources clipped at the loop's stop (`x1.clip`)."""
    out, rows, lines, _ = GX1.clip(out, decision_lines, lines)
    frames = E._frame_index(lines)[1]
    steps = e_steps(lines)
    return {"cadence": e_cadence(lines), "steps": steps, "engage_pull": e_pull(rows),
            "cone_bites": e_cone_bites(frames), "clock": e_clock(rows, lines),
            "crawler": e_crawler(frames, lines, steps), "room": e_room(frames),
            "rip_ride": e_rip_ride(rows, lines)}


# ---------------------------------------------------------------- the report and the grade
def _r(v, n=2):
    return round(v, n) if isinstance(v, float) else v


def _sh(s):
    s = E._d(s)
    return "%s/%s" % (s.get("n"), s.get("of"))


def lines_x6(g):
    """One report line per new reading (`NEW`), each clause marked reading."""
    cd, st, pl, cb, ck, cr, rm, rr = (E._d(g.get(k)) for k in NEW)
    out = []
    if cd.get("read"):
        rt = E._l(cd.get("retreats"))
        out.append("cadence (the press leaves) [reading]: %s presses, moving back %s, air %s, air at launch %s; done "
                   "lines %s; %s retreats, %s presses in them, %s on the moving back step" % (
                       cd.get("presses"), _sh(cd.get("moving_back")), _sh(cd.get("air")), _sh(cd.get("air_launch")),
                       cd.get("done"), len(rt), sum(r["presses"] for r in rt), sum(r["back"] for r in rt)))
    else:
        out.append(GX1._unread("cadence"))
    out.append("steps (the work leaf's reasons, as runs) [reading]: step_for %s, shove_for %s, repin_for %s, %s "
               "nan_heading lines; pile %s" % (st.get("step_for"), st.get("shove_for"), st.get("repin_for"),
                                               st.get("nan_heading"), st.get("pile"))
               if st.get("read") else GX1._unread("steps"))
    out.append("engage pull (%s) [reading]: %s lines, by why %s, spread at the episodes' first lines median %s" % (
        ENGAGE_PULL, pl.get("lines"), {k: (v["lines"], v["held"], v["closed"], v["clamped"], v["episodes"],
                                          _r(v["spread_first_median"])) for k, v in E._d(pl.get("by")).items()},
        _r(pl.get("spread_first_median"))) if pl.get("read") else GX1._unread("engage pull"))
    out.append("cone bites (onsets with the nearest standing more than %s degrees off the body) [reading]: %s of %s; "
               "%s" % (CONE_DEG, cb.get("outside"), cb.get("bites"), [(r["seq"], _r(r["angle"], 1))
                                                                       for r in E._l(cb.get("rows"))])
               if cb.get("read") else GX1._unread("cone bites"))
    out.append("clock (%s) [reading]: %s lines, %s allowed, %s held, %s cut, by action %s, waited %s s, %s started "
               "under the need, %s cares cut by a steer (superseded by %s), durations %s" % (
                   CLOCK, ck.get("lines"), ck.get("allowed"), ck.get("held"), ck.get("cut"), ck.get("by_action"),
                   _r(ck.get("waited")), ck.get("under"), ck.get("steer_cuts"), ck.get("superseded_by"),
                   {k: (v["n"], _r(v["median"], 3)) for k, v in E._d(ck.get("durations")).items()})
               if ck.get("read") else GX1._unread("clock"))
    out.append("crawler (a living crawler within %s tiles while pressing at a standing target) [reading]: %s frames, "
               "%s s; %s crawler_buffer steps" % (CRAWLER_R, cr.get("frames"), _r(cr.get("seconds")), cr.get("buffer"))
               if cr.get("read") else "crawler: no frame read")
    out.append("room (me.room) [reading]: %s frames, stops %s, roomMs p50 %s max %s; at the %s bite onsets with a ring "
               "(closed under %s tiles, behind closed of behind) %s" % (
                   rm.get("frames"), rm.get("stops"), rm.get("ms_p50"), rm.get("ms_max"), rm.get("bites_read"),
                   ROOM_NEED, [(b["seq"], b["closed"], b["behind_closed"], b["behind"]) for b in E._l(rm.get("bites"))])
               if rm.get("read") else GX1._unread("room"))
    out.append("rip ride (rips sent with %s against standing) [reading]: riding %s, standing %s" % (
        KEEP_MOVING, rr.get("riding"), rr.get("standing")) if rr.get("read") else GX1._unread("rip ride"))
    return out


def report_lines_x6(g):
    """grade_x5's report lines (`report_lines_x5`), its gate line naming gate_x6, then `lines_x6`."""
    g = E._d(g)
    base = GX5.report_lines_x5(g)
    return [("gate_x6 " + ln[len("gate_x5 "):]) if ln.startswith("gate_x5 ") else ln for ln in base] + lines_x6(g)


def grade_x6(record, decision_lines=None, state_dir=None, goal_lines=None, prev=None, lines=None, kind=None):
    """`grade_x5` under "grade_x6" (`base` "grade_x5", `base_x5` x5's own base, x5's nesting kept) with the engagement
    readings (`readings_x6`), over the state lines of `state_dir` unless `lines` is given (read once and handed down);
    its report lines `report_lines_x6`'s."""
    record = E._d(record)
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    g = GX5.grade_x5(record, decision_lines, state_dir, goal_lines, prev, lines, kind)
    if files and "frames_files" in g:
        g["frames_files"] = files
    g["base_x5"], g["base"], g["grade"] = g["base"], g["grade"], "grade_x6"
    g.update(readings_x6(record, decision_lines, lines))
    g["report_lines"] = report_lines_x6(g)
    return g


def gate_x6(outs):
    """gate_x5 (grade_x6 changes none of what it reads), named gate_x6."""
    return GX5.gate_x5(outs)
