"""Nothing changes offline (Angus, 2026-10-18; Plan 16 Task 2, spec section 1.1 and 1.2), through the whole server.

A stand-in player (the golden trace's decorator, named g4 so the trace's item-path Steak is its meal) plays 4 game hours
online on server_host.Host with a meal, a second bite, wine and tea late enough that the stomach, the meal pool and the
gut lane still hold them, a nicotine anchor and a nap, then logs out. The minute sees it leave; the world then runs on
for the gap; the player returns as a NEW object carrying the vanilla state it left with (the stats and the macro
stores the player save keeps). The return minute's first touch loads and resumes the record (NR_Server_Store's S.load,
K.resume), and the minute steps nothing: every record value and every written stat (HUNGER, THIRST, FATIGUE) is the
value at departure, and every stamp of K.resume.STAMPS has moved by the gap. The hour of day is held (getTimeOfDay
answers a constant), since the circadian and sleep-hour reads follow the world clock until Task 4's body clock (audit
L8); a 72 h gap returns at the same hour anyway.

Beside it: a 3 h stall while online and asleep is integrated in sub-steps with every booked hour of sleep kept; an
eat landed before the first step back decays no monotony across the gap; the record day closes after 24 online hours,
whatever the world day; and every world-age field of a stepped record is in K.resume.STAMPS or K.resume.KEPT.
"""
import math
import re

import pytest

from . import golden_trace as GT
from .golden_trace import walk, _Num

START = GT.START_AGE
HOUR = 13.8333                                  # the held hour of day (the circadian factor reads 1 near it)
NAME = "g4"
CFG = {"rate": 1.5, "inv": 6, "maxW": 8, "traits": ["NEEDS_MORE_SLEEP"], "asleep": [100, 160],
       "parts": {"Hand_L": {"cut": 5.0}}, "nicotine": 0.0}
MACROS = (1300.0, 150.0, 50.0, 70.0)
STATS = ("HUNGER", "THIRST", "FATIGUE")
HELD = ("getGameTime = function() return { getWorldAgeHours = function(s) return NR_T.age end, "
        "getTimeOfDay = function(s) return NR_T.hour end } end")


def host():
    h = GT.new_host()
    h.rt.execute(HELD)
    h.T.hour = HOUR
    return h


def new_player(h, cfg=None, sv=None, nut=None):
    p = h.player(NAME, *MACROS)
    c = dict(CFG if cfg is None else cfg)
    c["hunger"], c["thirst"], c["fatigue"] = 0.30, 0.20, 0.20
    lcfg = h.rt.table()
    for k, v in c.items():
        if isinstance(v, list):
            lcfg[k] = h.rt.table(*v)
        elif isinstance(v, dict):
            parts = h.rt.table()
            for pn, fields in v.items():
                parts[pn] = h.rt.table_from(fields)
            lcfg[k] = parts
        else:
            lcfg[k] = v
    p = h.T.decorate(p, lcfg)
    if sv is not None:                          # the player save's stats and macro stores, carried to the new object
        for k, v in sv.items():
            p.sv[k] = v
    if nut is not None:
        for k, v in nut.items():
            p.nut[k] = v
    return p


def minute(h, age, m=None):
    h.T.age = age
    if m is not None:
        h.T.m = m
    h.T.engine()
    h.minute()
    h.tick(25)


def fluid(h, kind, litres):
    src = h.NR.data.fluids.get(kind)
    h.NR.server.intake.land(h.record(NAME), NAME, h.K.vector.fluid(src, litres))


def play(h, minutes=240):
    """4 game hours online from START: the Steak at 10 (item path), the second bite at 70, the nicotine rise at 25,
    a nap 100-160, a second Steak at 200, wine and tea at 220. Returns the player and the last age."""
    p = new_player(h)
    h.online(p)
    age = START
    for m in range(1, minutes + 1):
        age = START + m / 60.0
        h.T.age, h.T.m = age, m
        if m in (10, 200):
            h.T.eat(10, NAME)
        if m == 70:
            h.T.eat(70, NAME)
        if m == 25:
            p.sv.NICOTINE_WITHDRAWAL = 0.4
        if m == 220:
            fluid(h, "Wine", 0.25)
            fluid(h, "Tea", 0.25)
        minute(h, age)
    return p, age


def snapshot(h, p):
    rec = walk(h.record(NAME))
    stats = {k: p.sv[k] for k in STATS}
    return rec, stats


def leaves(d, prefix=""):
    out = {}
    for k, v in d.items():
        path = prefix + k
        if isinstance(v, dict):
            out.update(leaves(v, path + "."))
        else:
            out[path] = v.text if isinstance(v, _Num) else v
    return out


def stamp_paths(h, rec_leaves):
    """The leaves of a walked record that K.resume.STAMPS names."""
    pats = []
    for i in range(1, len(h.K.resume.STAMPS) + 1):
        s = h.K.resume.STAMPS[i]
        pats.append(re.compile("^" + re.escape(s).replace(r"\*", ".+") + "$"))
    return {k for k in rec_leaves if any(pt.match(k) for pt in pats)}


def leave_and_return(h, p, dep, gap_h, eat_first=False):
    """The player leaves after the minute at dep, the minute sees it gone, and it returns gap_h game hours after dep as
    a new object carrying its stats and macro stores. eat_first lands the trace's Steak with the new object before the
    return minute's queue slot (the eat's touch is the sight's first). Returns the new object and the return age."""
    sv = {k: p.sv[k] for k in ("HUNGER", "THIRST", "FATIGUE", "ENDURANCE", "STRESS", "UNHAPPINESS", "BOREDOM",
                               "NICOTINE_WITHDRAWAL", "TEMPERATURE", "INTOXICATION", "PANIC", "FOOD_SICKNESS")}
    nut = {k: p.nut[k] for k in ("cal", "carb", "lip", "pro", "weight")}
    h.online()
    minute(h, dep + 1 / 60.0)                   # the minute that sees the departure (the store's flush is queued)
    ret = dep + gap_h
    q = new_player(h, sv=sv, nut=nut)
    h.online(q)
    h.T.age = ret
    if eat_first:
        h.T.eat(10, NAME)
    h.minute()
    h.tick(25)
    return q, ret


@pytest.mark.parametrize("gap_h", [72.0, 0.5, 59 / 60.0])
def test_a_logout_changes_nothing(gap_h):
    h = host()
    p, dep = play(h)
    rec0, stats0 = snapshot(h, p)
    q, ret = leave_and_return(h, p, dep, gap_h)
    rec1, stats1 = snapshot(h, q)
    assert h.NR.server.store.stats.resumes == 1 and h.NR.server.players.stalls == 0
    a, b = leaves(rec0), leaves(rec1)
    stamps = stamp_paths(h, a)
    assert {"lastSeen", "kineticsAge", "satiety.t", "satiety.nicH", "nutrients.lastAgeH", "body.lastAgeH",
            "body.dayStartH", "acute.winStartH", "acute.mass90ageH", "acute.lastFedAgeH", "acute.lastVigAgeH",
            "drain.fedAgeH", "monotony.t.Base.Steak.last"} <= stamps
    # the record's sub-tables the scenario must cover: the stomach and meal pool, nutrients, fluids, the body, acute
    # (caffeine, alcohol, hangover, sleep), monotony, the drain clocks and the record day
    for k in ("stomach.buffer.calories", "stomach.liquid", "satiety.M", "satiety.S", "nutrients.vitC.p", "fluids.water",
              "body.fm", "body.inDay", "body.trail.ee.1", "acute.caf", "acute.gutCaf", "acute.alc", "acute.gutAlc",
              "acute.hang", "acute.debtH", "acute.winSleptH", "acute.awakeH", "monotony.t.Base.Steak.n",
              "drain.acuteH", "body.dayIndex"):
        assert k in a, k
    assert float(a["stomach.buffer.calories"]) > 50 and float(a["acute.gutAlc"]) > 0 and float(a["acute.gutCaf"]) > 0
    changed = sorted(k for k in set(a) | set(b) if k not in stamps and a.get(k) != b.get(k))
    assert changed == [], changed
    for k in stamps:                            # every stamp moved by the gap (those at the last step exactly onto ret)
        x0, x1 = float(a[k]), float(b[k])
        assert x1 == pytest.approx(x0 + (ret - dep), abs=1e-9), k
    for k in ("lastSeen", "kineticsAge", "satiety.t", "nutrients.lastAgeH", "body.lastAgeH"):
        assert float(b[k]) == ret, k
    assert stats1 == stats0                     # the written HUNGER, THIRST and FATIGUE
    # and the next online minute integrates one minute, not the gap
    minute(h, ret + 1 / 60.0)
    assert float(leaves(walk(h.record(NAME)))["nutrients.lastAgeH"]) == ret + 1 / 60.0
    assert h.NR.server.players.stalls == 0


def test_a_reconnect_the_minute_never_saw_is_still_a_sight():
    # the absence is keyed on the player object: a player that left and came back between two minute events (the walk
    # never saw it gone, so no departure fired) returns as a new object, and the store's first touch with it resumes
    # the record, so the 2 h away are frozen, never integrated as a stall
    h = host()
    p, dep = play(h)
    rec0, stats0 = snapshot(h, p)
    sv = {k: p.sv[k] for k in ("HUNGER", "THIRST", "FATIGUE", "NICOTINE_WITHDRAWAL")}
    q = new_player(h, sv=sv, nut={k: p.nut[k] for k in ("cal", "carb", "lip", "pro", "weight")})
    h.online(q)                                 # the old object gone and the new one in, between two minutes
    minute(h, dep + 2.0)
    rec1, stats1 = snapshot(h, q)
    assert h.NR.server.store.stats.resumes == 1 and h.NR.server.players.stalls == 0
    a, b = leaves(rec0), leaves(rec1)
    stamps = stamp_paths(h, a)
    assert sorted(k for k in set(a) | set(b) if k not in stamps and a.get(k) != b.get(k)) == []
    assert stats1 == stats0


def test_a_restart_while_away_changes_nothing_and_writes_nothing_at_the_return():
    # the record read back from its slot file holds only its inputs (K.store.inputsOnly): the load fills it and the
    # resume moves its stamps; the return minute runs nothing, so no stat is written from a record whose derived fields
    # the next minute has yet to rebuild, and the next minute rebuilds them
    h = host()
    p, dep = play(h)
    store = h.NR.server.store
    inputs0 = leaves(walk(h.K.store.inputsOnly(h.record(NAME))))
    stats0 = {k: p.sv[k] for k in STATS}
    sets0 = p.wst.sets
    h.online()
    minute(h, dep + 1 / 60.0)
    store.records[NAME] = h.K.store.inputsOnly(h.record(NAME))     # the restart: the file's copy, a new table
    sv = {k: p.sv[k] for k in ("HUNGER", "THIRST", "FATIGUE", "NICOTINE_WITHDRAWAL")}
    q = new_player(h, sv=sv, nut={k: p.nut[k] for k in ("cal", "carb", "lip", "pro", "weight")})
    h.online(q)
    ret = dep + 30.0
    minute(h, ret)
    assert store.stats.resumes == 1 and q.wst.sets == 0
    assert {k: q.sv[k] for k in STATS} == stats0
    inputs1 = leaves(walk(h.K.store.inputsOnly(h.record(NAME))))
    stamps = stamp_paths(h, inputs0)
    assert sorted(k for k in set(inputs0) | set(inputs1) if k not in stamps and inputs0.get(k) != inputs1.get(k)) == []
    assert h.record(NAME).fluids.thirstTarget is None              # derived: not yet rebuilt
    minute(h, ret + 1 / 60.0)
    assert h.record(NAME).fluids.thirstTarget is not None and q.wst.sets > 0
    assert sets0 > 0


def test_a_stall_online_integrates_every_hour_in_sub_steps_and_keeps_the_booked_sleep():
    # audit L6 (spec section 1.1): a 3 h step on the same object (a slow server, the fast-forwarded night) is online
    # time: 3 sub-steps of 60 minutes, so the sleep the minute books is the whole 3 h (until Plan 16 the step was
    # clamped at 60 minutes and 2 h of booked sleep were lost)
    h = host()
    cfg = dict(CFG, asleep=[0, 10 ** 6])
    p = new_player(h, cfg=cfg)
    h.online(p)
    for m in range(1, 31):
        minute(h, START + m / 60.0, m)
    a = h.record(NAME).acute
    slept0, win0, lean0 = a.winSleptH, a.winStartH, h.record(NAME).body.lm
    assert a.sleptH > 0 and slept0 > 0
    minute(h, START + 30 / 60.0 + 3.0, 31)      # the stall
    P = h.NR.server.players
    assert P.stalls == 1 and P.substeps == 3
    assert a.winStartH == win0                  # the window did not close in the stall
    assert a.winSleptH == pytest.approx(slept0 + 3.0, abs=1e-9)
    assert h.record(NAME).lastSeen == START + 30 / 60.0 + 3.0
    assert h.NR.server.store.stats.resumes == 0


def test_a_stall_past_a_day_of_sub_steps_freezes_its_excess():
    h = host()
    p = new_player(h)
    h.online(p)
    for m in range(1, 4):
        minute(h, START + m / 60.0, m)
    r = h.record(NAME)
    day0 = r.body.dayStartH
    minute(h, START + 3 / 60.0 + 30.0, 4)       # 30 h on the same object: 24 sub-steps, 6 h frozen
    P = h.NR.server.players
    assert P.stalls == 1 and P.substeps == 24
    assert r.body.dayStartH == pytest.approx(day0 + 6.0 + 24.0, abs=1e-9)   # moved 6 h, then one close
    assert r.body.dayIndex == math.floor(START / 24) + 1


def test_an_eat_before_the_first_step_back_decays_no_monotony_across_the_gap():
    # audit L3: the eat's touch is the sight's first, so the resume runs before the landing; the type's count after
    # the eat is the one an eat at the departure minute would leave (the decay counts online time only)
    def arm(gap_h):
        h = host()
        p, dep = play(h)
        if gap_h == 0:
            h.T.age = dep
            h.T.eat(10, NAME)
        else:
            leave_and_return(h, p, dep, gap_h, eat_first=True)
        return h, h.record(NAME).monotony.t["Base.Steak"]
    h0, e0 = arm(0)
    h1, e1 = arm(72.0)
    assert h1.NR.server.store.stats.resumes == 1
    assert e1.n == pytest.approx(e0.n, rel=1e-12) and e0.n > 0.25   # two Steaks before, the third at the return
    assert e1.last == pytest.approx(e0.last + 72.0, abs=1e-9)


def test_the_record_day_closes_after_24_online_hours_whatever_the_world_day():
    # spec section 1.2 (audit L2): born at 100.5 the record day runs from 96.0; 10.25 h away across the world's day
    # boundary at 120.0 moves it to 106.25, so it closes at 130.25, never at 120.0, and the next closes 24 online
    # hours later
    h = host()
    p = new_player(h)
    h.online(p)
    age0 = 100.5
    minute(h, age0, 1)
    r = h.record(NAME)
    assert r.body.dayStartH == 96.0 and r.body.dayIndex == 4
    age = age0
    for k in range(1, 20):                      # online to 110.0 in 30-minute steps
        age = age0 + k * 0.5
        minute(h, age, 1 + k)
    q, ret = leave_and_return(h, p, age, 10.25)
    r = h.record(NAME)
    assert r.body.dayStartH == pytest.approx(96.0 + 10.25, abs=1e-9) and r.body.dayIndex == 4
    t = ret
    while t < 130.25 - 1e-9:                    # past the world boundary at 120: nothing closes
        t = min(t + 0.5, 130.25 - 1 / 60.0)
        minute(h, t)
        assert r.body.dayIndex == 4, t
        if t >= 130.25 - 1 / 60.0:
            break
    minute(h, 130.25)
    assert r.body.dayIndex == 5 and r.body.dayStartH == pytest.approx(130.25, abs=1e-9)
    assert r.nutrients.lastDayIndex == 5


def test_every_world_age_field_is_a_stamp_or_kept():
    # the single list (K.resume.STAMPS): a record field ending AgeH, At or Stamp, and any numeric leaf that equals a
    # step age the run visited (a world age stamped at a minute), is a stamp the resume moves or a field it keeps
    h = host()
    p, dep = play(h)
    q, ret = leave_and_return(h, p, dep, 72.0)
    for m in range(1, 31):
        minute(h, ret + m / 60.0)
    rec = leaves(walk(h.record(NAME)))
    stamps = stamp_paths(h, rec)
    kept = set(walk(h.K.resume.KEPT))
    named = {k for k in rec if re.search(r"(AgeH|At|Stamp)$", k.split(".")[-1])}
    assert named and named <= stamps | kept, named - stamps - kept
    ages = {START + m / 60.0 for m in range(0, 241)} | {ret + m / 60.0 for m in range(0, 31)}
    hits = set()
    for k, v in rec.items():
        if isinstance(v, str):
            try:
                x = float(v)
            except ValueError:
                continue
            if any(abs(x - a) < 1e-9 for a in ages):
                hits.add(k)
    assert hits and hits <= stamps | kept, hits - stamps - kept
