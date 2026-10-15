"""The energy and exercise-lag oracles on the shipped server pipeline (Plan 11f Task 2b, ruling F1-2; the oracles since Plan
11f Task 2c, option (b) of task-2b-options.md): a server-path replay of each study, through tools/replay_live.py's server
backend (ServerReplay: the mod's own adapters in their ORDER on the golden stand-ins). Each test grades its study's
band and pins its readings. The simplified-path energy oracles these replace (the 36 h fast, the steady eater, six
meals against three live, the low-carbohydrate day, Karl 2021, King 2011 at steady state and the S1255 arithmetic in
test_satiety_meal_studies.py and test_satiety_activity.py) were deleted with the deficit drive's refit on this path
(Plan 11f Task 2c, from 7500 and 1.0; its fix round 1 widened the search to K.deficit.EX_BYPASS_HI and EX_BYPASS_LO and
ranked the candidates by the worst case over twin K's plausible alternatives, the walk billed ClimbRope, Running10kmh
or loaded Walking5kmh and no battery: K.deficit.BALANCE_SPAN_KCAL 3100, K.deficit.DEFICIT_FLOOR 0.02, EX_BYPASS_HI 0.575
and EX_BYPASS_LO 0.28); test_replay_live_oracle.py keeps the simplified composition only as the reference of the
replay tool's oracle backend.

Plan 11g Task 7 refit the drive on the deficit studies alone (tools/fit_deficit_drive.py over deficit_oracles.py, the
registry where every band below lives; fit-11g-deficit-20261012 and its plateau scan 20261012b): the 36 h fast's two
days, Karl's DEF arm at the worst of twin K's five billings and King 2011 scored; Karl's BAL arm, carried by satiety
since Plan 11g Task 6c, held inside S1892's -64 to -46 % as a constraint with the steady eater, six against three and
S1255; Whybrow and E-MECHANIC fixed (no fitted constant moves the lag). The constants: BALANCE_SPAN_KCAL 3970.55,
EX_BYPASS_LO 0.282, EX_BYPASS_HI 0.44 (moved to mid-plateau, 0.405, in the task's fix round 1, ruling T7-6), and the
deficit floor at its bound 0 (removed in that round, ruling T7-1).

What the server path adds to every oracle: an eat reaches the trailing-24 h window only as the stomach empties
(ctx.absorbed), the day partition moves fm and lm (fatDep enters the energy state), adaptive thermogenesis and the
training close run, and the expenditure is billed off the stand-in's metabolic rate by class (K.energy.classOf, the
Compendium bill), never injected. The stand-in idles at the engine's Default class (1.5, billed 1.3, standing quietly).

The replays, and where each departs from the study or the deleted oracle (each departure a choice named here):
- The 36 h fast, the steady eater, six meals against three (live) and the low-carbohydrate day: the oracles' own event
  lists on the 70 kg man (male, responder 1), asleep 23:00-07:00, as test_replay_live_oracle.py runs them. Six against
  three's warm-up eats fill the stomach and M at the eat (the server has no energy-only eat). Six against three held is
  the satiety replay at the energy state 1 (kinetics and the writer alone, no body), from M 0 at 08:00.
- Karl 2021 (S1325), twin K (Plan 11f Task 2c, ruling 2b-3): Karl as the paper ran it, from its own numbers
  (docs/superpowers/research/2026-10-10-live-study-replays/03-karl-2021-facts.md). It replaces Task 2b's twins E, Env,
  V and C, whose bodies and expenditures no row gave. Each choice the paper leaves open is named:
    body     87.3 kg (Hennigar 2021, the same n = 10 of the same trial), male, built by the stand-in's own birth
             composition (K.body.split at 87.3 kg, no build flags: lm 67.8 kg, REE 1,748 kcal); the paper reports no
             height or body fat;
    clock    asleep 01:00-05:00 on the three SUSOPS nights (the paper's); the nights before them and REST's 22:00-06:00
             (an ASSUMED unrestricted 8 h, so REST carries no sleep debt; REST ran 06:00-18:00); two sedentary warm-up
             days at REST intake (ASSUMED) fill the trailing window and seed the pool; meals at 07:00, 12:00 and 18:00
             (the paper matched meal times across arms but gives no clock; the oracle's);
    work     the morning loaded walk 08:00-09:04 (64 min at 8.3 MET), the evening loaded walk 19:30-21:32 (122 min at
             8.4 MET), the afternoon walk 14:00-15:34 (94 min at 5.4 MET); the clock times are ASSUMED. The server bills
             one class a minute, and none bills 8.3: the loaded walks alternate HeavyWork (engine 6.0, billed 6.0) and
             Running10kmh (engine 6.9, billed 9.3) minute by minute, a Bresenham share (44 of 64 and 88 of 122 minutes
             at 9.3) billing 8.27 and 8.38 MET on the bout's mean, vigorous aerobic every minute as loaded walking is
             (the nearest single class, ClimbRope's 8.0, would class the walk as resistance work: a reading in the
             report). The 5.4 MET walk bills DiggingSpade (engine 5.5, billed 5.0, not vigorous: every class at or
             above 6.0 is vigorous on the server), 0.4 MET short (about 55 kcal a day at 87.3 kg). The task battery
             runs 10:00-10:25 at MediumWork (billed 4.0): an ASSUMED 25 min, the length that bills the protocol's
             "approximately 100 kcal/d" above the idle class;
    intake   the paper's, REST 10.6, DEF 10.5 and BAL 22.7 MJ/d (Table 1), as three equal mixed meals, water 300 g per
             1,950 kcal (the oracle's); the paper's snacks on request are not modelled;
    reading  the study's 8 VAS times a day, before and after each meal (the minute before the eat lands and the minute it
             lands) and before and after the morning walk (its first minute's eve and its last minute), over the three
             SUSOPS days, against one REST day read at the same 8 times; the outcome is the percentage difference of the
             mean ratings against REST's (Table 2's quantity).
  The calibration check: the twin's work days bill 19.75-19.88 MJ (DEF) and 19.79-20.02 MJ (BAL) against the
  doubly-labelled-water TDEE of 19.1 and 20.0 MJ/d (Table 1, n 9); the body is not tuned to close the gap. Its
  sedentary day bills 9.06 MJ against REST's 10.6 MJ diet (RMR x 1.3 in the paper): the warm-up and REST days run a
  surplus of about 370 kcal a day.
- King 2011 at steady state (S1312): the oracle's 2,500 kcal day as the stand-in's idle day awake 16 h (116.0 kg),
  asleep 23:00-07:00 (the oracle has no night), the 4715 kJ run as 73 min of Running10kmh (engine 6.9, billed 9.3,
  vigorous aerobic) from 08:00 of day 3.
- Whybrow 2008 (S1318) and E-MECHANIC (S1320, S1664): the lag share, lagged(record.satiety.L) over the day's bout kcal
  (read off body.exKcalDay across the bout), as the oracles read lagged(L) over the bout's kcal. Never asleep (the
  oracles' bout is at 02:00), meals of the idle day plus the bout at 08:00, 13:00 and 20:00. Whybrow: the 70 kg man,
  Running15kmh (billed 14.8) for 53 and 27 min (3.5 and 1.75 MJ). E-MECHANIC: the oracle's 90 kg, 60 min a day of
  MediumWork (243 kcal against the high dose's 257) and UsingTools (108 kcal against the low dose's 103), on a
  30-minute synthetic step: the lag kernel is the exact solution for an input constant over its step, so the step
  does not move L where the bout fills whole steps (the 24-week runs take 24,192 steps where minutes would take
  241,920).
- S1255: the deleted oracle was K.deficit.state's arithmetic, path-independent; the replay here is the 70 kg man eating
  75 % of his maintenance for a week, the request-level rise read off the energy state the pipeline stamps on day 7.
Only `host`; no `parametrize`.
"""
import os
import sys
from .participant import PARTICIPANT

from . import test_satiety_activity as A
from . import test_satiety_meal_studies as M
from .server_host import REPO
from .test_replay_live_oracle import energy_run, fast_plans, meal_events, sleep_events

sys.path.insert(0, os.path.join(REPO, "tools"))
import replay_live as RL  # noqa: E402

MAN = {"player": {"weight": 70.0, "female": False}, "rng": "half"}
RATE = {"HeavyWork": 6.0, "MediumWork": 3.9, "UsingTools": 2.5, "Running10kmh": 6.9, "Running15kmh": 9.5, "DiggingSpade": 5.5}
IDLE = 1.5                        # the engine's Default class (a live idle player, #2875)


def ex_per_min(host, cls, w):
    """The exercise kcal a minute at class cls for a w kg stand-in: the billed MET above the idle class x mass / 60."""
    return (host.K.energy.COMPENDIUM[cls] - host.K.energy.COMPENDIUM.Default) * w / 60.0


def idle_day(host, w, awake_h):
    """A w kg man's idle day: REE off his birth lean mass plus the Default class's bill above rest while awake."""
    host.rt.execute(PARTICIPANT)
    b = host.G.NR_participant(w, 1, 0)                 # the study participant (participant.py, Plan 13 Task 12)
    return host.K.energy.ree(b.lm) + (host.K.energy.COMPENDIUM.Default - host.K.energy.MET_REST) * w * awake_h


def test_the_server_rows_read_body_eb24_as_the_metabolism_step_does(host):
    # tools/replay_live.py's derived path (Task 2b): the record stores no eb24; the row reads K.energy.eb24h(body) after
    # the drain, the balance the step handed to activityState (the oracle backend's alias of the same name)
    ev = [{"minute": 30, "kind": "meal", "size": 600.0}]
    rows, be = RL.replay_arm(ev, minutes=240, backend="server", paths=("body.eb24",), **MAN)
    body = be.record()["body"]
    assert rows[-1]["body.eb24"] == be.K.energy.eb24h(body)
    assert rows[-1]["body.eb24"] == be.K.body.trail24(body.trail, "kcal") - be.K.body.trail24(body.trail, "ee")
    assert rows[20]["body.eb24"] < 0 < rows[-1]["body.eb24"]      # the meal empties into the window over the hours


# --- the 36 h fast, the steady eater, six against three, the low-carbohydrate day (the 70 kg man) ----------------

def fast_server():
    fed, fast, days = fast_plans()
    paths = ("body.energyState", "body.eb24", "acute.g")
    _, bf = energy_run(fed, days, backend="server", **MAN)
    ev = sleep_events(days) + [{"minute": m, "kind": "meal", "size": k} for m, k in sorted(fast.items())]
    ev.sort(key=lambda e: e["minute"])
    rx, bx = RL.replay_arm(ev, minutes=days * 1440, backend="server", paths=paths, **MAN)
    W = M.FAST_WARM_DAYS
    ifed, ifast = RL.intake_by_day(bf.eats), RL.intake_by_day(bx.eats)
    at = [M.at_hour(0, 20 + 12), M.at_hour(0, 20 + 24), M.at_hour(0, 20 + 36)]
    return {"r2": ifast[W + 2] / ifed[W + 2], "r3": ifast[W + 3] / ifed[W + 3], "fed": [ifed[W + 2], ifed[W + 3]],
            "fast": ifast[W + 2], "log": [{k: rx[m - 1][k] for k in paths} for m in at]}


def steady_server():
    plan = {}
    for d in range(M.STEADY_DAYS):
        plan.update({int(d * 1440 + h * 60): ("maint" if d == 0 else "request") for h in M.FAST_MEAL_H})
    rows, be = energy_run(plan, M.STEADY_DAYS, backend="server", **MAN)
    by = RL.intake_by_day(be.eats)
    hours = [int((M.STEADY_DAYS - 1) * 1440 + h * 60) for h in range(1, 25)]
    return [by[d] / be.maint() for d in (1, 2, 3)], [rows[m - 1]["body.energyState"] for m in hours]


def six_live_sum(n, gap):
    start = M.SIX_WARM_DAYS * 1440 + 480
    ev = sleep_events(M.SIX_WARM_DAYS + 2)
    wk = 2000.0 / 3
    for d in range(M.SIX_WARM_DAYS):
        for i in range(3):
            ev.append({"minute": d * 1440 + 480 + i * 300, "kind": "eat",
                       "vec": M.mixed(wk, water=300.0, fibre=6.0 * wk / 650)})
    k = 2000.0 / n
    for i in range(n):
        ev.append({"minute": start + i * gap, "kind": "eat", "vec": M.mixed(k, water=900.0 / n, fibre=6.0 * k / 650)})
    ev.sort(key=lambda e: e["minute"])
    rows, _ = RL.replay_arm(ev, minutes=(M.SIX_WARM_DAYS + 2) * 1440, backend="server", **MAN)
    total = 0.0
    for r in rows[start:start + 1440]:            # in order, as the oracle's Lua sums
        total = total + r["HUNGER"]
    return total


def six_held_sum(n, gap):
    k = 2000.0 / n
    events = {i * gap: [("food", M.mixed(k, water=900.0 / n, fibre=6.0 * k / 650))] for i in range(n)}
    a0 = 8.0
    start = {"username": "admin", "firstSeen": a0, "lastSeen": a0, "kineticsAge": a0,
             "satiety": {"M": 0.0, "S": 0, "L": 0, "t": a0}}
    rows, _ = RL.replay_arm(meal_events(events), start=start, minutes=1440, start_age=a0, steps=("kinetics", "writer"))
    total = 0.0
    for r in rows:
        total = total + r["HUNGER"]
    return total


def lowcarb_server():
    """lowcarb_reading's two arms on the server: (the mixed arm at 08:00 and 20:00 on day 1, the low arm at 20:00)."""
    paths = ("body.energyState", "body.eb24", "acute.g")
    m8, m20 = M.at_hour(1, 8), M.at_hour(1, 20)
    days = M.FAST_WARM_DAYS + 2
    out = {}
    for arm in ("mixed", "low"):
        ev = sleep_events(days)
        plan = M.warm()
        plan.update(M.meals_of(0, "maint"))
        plan.update(M.meals_of(1, "maint" if arm == "mixed" else "lowcarb"))
        for m, kind in sorted(plan.items()):
            ev.append({"minute": m, "kind": "meal", "size": "maint", "lowcarb": kind == "lowcarb"})
        ev.sort(key=lambda e: e["minute"])
        rows, be = RL.replay_arm(_lowcarb_comp(ev), minutes=days * 1440, backend="server", paths=paths, **MAN)
        out[arm] = {m: {k: rows[m - 1][k] for k in paths} for m in (m8, m20)}
    return out["mixed"][m8], out["mixed"][m20], out["low"][m20]


def _lowcarb_comp(ev):
    """The low-carbohydrate meal's composition (ENERGY_REPLAY's: 50 g/d, 20 % protein, fat the rest) on the 70 kg
    man's maintenance (1,948.73 kcal, R.maint); the mixed meals keep the default."""
    maint = 1948.7298
    c = M.FAST_LOWCARB_G * 4 / maint
    out = []
    for e in ev:
        e = dict(e)
        if e.pop("lowcarb", False):
            e["comp"] = {"p": 0.20, "c": c, "f": 1 - 0.20 - c}
        out.append(e)
    return out


def test_the_36_h_fast_on_the_server_path(host):
    # S1613 (Johnstone 2002: 12.2 against 10.2 MJ the day after a 36 h fast, 1.20) and S1614 (Clayton 2016: day 3 not
    # different, 1.0), each within 1.1x (ruling 11c-30); ruling 11d-3's direction, day 2 above 1 and day 3 below it.
    # Since the refit on the deficit studies alone (Plan 11g Task 7): day 2 1.148 (0.957x S1613; 1.196 in Plan 11f Task
    # 2c fix 1, 1.174 in its Task 2c, 1.342 at 7500 / 1.0), day 3 0.981 (0.969 before); the fed arm eats 1,948 and 1,941
    # kcal, the fast arm 2,236 on day 2 (2,333 in Plan 11f Task 2c fix 1, 2,637 before). At 12, 24 and 36 h of the fast
    # es reads 1.001, 1.164 and 1.249 (1.001, 1.21 and 1.318 at 3100 / 0.02; 1.001, 1.087 and 1.134 at 7500 / 1.0), eb24
    # -1, -1300 and -1945 and g 1.0, 0.946 and 0.766 (the balance and g do not move with the drive). Under Plan 13 Task 12's lean partition at the day close the
    # fed arm eats 1,947 and 1,940 kcal and the fast arm 2,235 on day 2 (the ratios, es, eb24 and g hold their roundings).
    # Under Plan 13 Task 10c's low-fat ramp (no fat term below a depletion of 0.10): day 2 1.145 (0.954x S1613), day 3
    # 0.979; the fed arm 1,946 and 1,939 kcal, the fast arm 2,228; es at 12, 24 and 36 h 1.0, 1.164 and 1.245
    f = fast_server()
    assert f["r2"] > 1 and f["r3"] < f["r2"], f
    assert M.ratio(f["r2"], 1.20) <= M.TOL and M.ratio(f["r3"], 1.0) <= M.TOL, f
    assert (round(f["r2"], 3), round(f["r3"], 3)) == (1.145, 0.979), f
    assert [round(x) for x in f["fed"]] == [1946, 1939] and round(f["fast"]) == 2228, f
    assert [round(x["body.energyState"], 3) for x in f["log"]] == [1.0, 1.164, 1.245], f
    assert [round(x["body.eb24"]) for x in f["log"]] == [-1, -1300, -1945], f
    assert [round(x["acute.g"], 3) for x in f["log"]] == [1.0, 0.946, 0.766], f


def test_the_steady_eater_on_the_server_path(host):
    # a balanced eater reads balance at every hour, and a request-level eater eats maintenance: STEADY_TOL 0.03. Days 2-4
    # at 0.9995, 0.9958 and 0.9966 x maintenance under Plan 11g Task 7's refit (1.0011, 0.9956 and 0.997 at 3100 / 0.02;
    # 1.0083, 0.9956 and 1.0007 at 7500 / 1.0), es 1.0017 to 1.002 over day 5 (1.0018 to 1.0022; 1.0007 to 1.0011): the
    # 20:00 dinner empties after midnight into the hour-slotted window. Under Plan 13 Task 12's lean partition at the day close: 0.9994, 0.9957 and 0.9964, es 1.0016
    # to 1.0019. Under Plan 13 Task 10c's low-fat ramp: 0.9988, 0.995 and 0.9957, es 1.0008 to 1.0012
    ratios, es = steady_server()
    assert all(abs(r - 1) <= M.STEADY_TOL for r in ratios) and all(abs(e - 1) <= M.STEADY_TOL for e in es)
    assert [round(r, 4) for r in ratios] == [0.9988, 0.995, 0.9957], ratios
    assert (round(min(es), 4), round(max(es), 4)) == (1.0008, 1.0012), es


def test_six_meals_against_three_on_the_server_path(host):
    # S1608 (1.14) and S1607 (null): the ratio within [0.9, 1.3] (ruling 11d-3). Held at es 1 the server's satiety path
    # is the satiety oracle's to 1e-12 (0.974 under Plan 11g Task 6c fix 1's and fix 2's refits; 0.951 under Task 6c's fit; 1.020
    # under the gut stage G's fit, Task 6; 1.004 under G's provisional constants; 0.969 on the P model); live it reads
    # 0.982 under the deficit refit (Task 7; 0.985 under Task 6c fix 2's satiety refit, 0.986 under fix 1's, 0.962 under Task 6c's fit, 1.033 under the gut stage's fit, 1.016 under its provisional
    # constants, 0.981 on the P model, 0.987 at 7500 / 1.0)
    held = six_held_sum(6, 150) / six_held_sum(3, 300)
    live = six_live_sum(6, 150) / six_live_sum(3, 300)
    assert abs(held - M.meal_frequency_ratio(host)) < 1e-12 and round(held, 3) == 0.974, held
    assert 0.9 <= live <= 1.3 and round(live, 3) == 0.982, live


def test_the_low_carbohydrate_day_on_the_server_path(host):
    # C9: the low arm runs g down at 20:00 of day 1 (0.967; the oracle 0.951), and at equal intake the two arms read the
    # same es on the server as on the oracle (ruling T4-1: g does not enter the energy state)
    m8, m20, low = lowcarb_server()
    assert round(m8["acute.g"], 3) == READ["lowcarb_g"][0] and round(m20["acute.g"], 3) == READ["lowcarb_g"][1], (m8, m20)
    assert round(low["acute.g"], 3) == READ["lowcarb_g"][2], low
    assert round(low["body.energyState"] - m20["body.energyState"], 4) == READ["lowcarb_des"], (low, m20)


# --- Karl 2021 (S1325): twin K, the paper's own numbers --------------------------------------------------------------

KARL_KG = 87.3                    # Hennigar 2021 (the same trial's n = 10): 87.3 +- 10.9 kg
KCAL_PER_MJ = 1000 / 4.184
KARL_MJ = {"REST": 10.6, "DEF": 10.5, "BAL": 22.7}     # Table 1, dietary intake, MJ/d
KARL_TDEE_MJ = {"DEF": 19.1, "BAL": 20.0}              # Table 1, doubly labelled water, MJ/d (n 9)
KARL_MEALS = (7, 12, 18)          # ASSUMED clock (the oracle's): the paper matched meal times but gives none
KARL_WARM = 2                     # ASSUMED sedentary days at REST intake before each arm
KARL_NIGHT = 22                   # ASSUMED unrestricted nights, 22:00-06:00, before SUSOPS and around REST
KARL_AM = (8 * 60, 64, 8.3)       # the morning loaded walk: 08:00 (ASSUMED), 64 min, 8.3 MET
KARL_EVE = (19 * 60 + 30, 122, 8.4)   # the evening loaded walk: 19:30 (ASSUMED), 122 min, 8.4 MET
KARL_PM = (14 * 60, 94)           # the afternoon walk: 14:00 (ASSUMED), 94 min at 5.4 MET, billed DiggingSpade 5.0
KARL_BATTERY = (10 * 60, 25)      # the task battery: 10:00 (ASSUMED), 25 min of MediumWork, about 100 kcal (the protocol)


def karl_walk(start, dur, met, vigorous=True):
    """A loaded walk billing `met` on the bout's mean: HeavyWork (billed 6.0) for the first minutes and Running10kmh
    (billed 9.3) for the last int(dur * (met - 6.0) / 3.3), every minute vigorous aerobic; idle after. The walk moves
    (Plan 11f C-17): a still stand-in's step down from Running10kmh to HeavyWork reads as a falling rate and bills idle
    (BAL -43.9 and DEF +26.7, both inside, with 1.5 MJ a day less billed), where a walker's moving flag keeps the class;
    fix 1 (ruling C17-5) caps a moving fall at Walking5kmh, so the Running minutes close the bout and the rate never
    steps down inside it (the readings are those of the interleaved walk: BAL -45.1, DEF +30.2).
    Not vigorous: the same kcal above the idle class billed at DiggingSpade (5.0, under the bar), so the bout runs
    longer. Returns (the bout's minutes, its events)."""
    x = (met - 6.0) / (9.3 - 6.0)
    if not vigorous:
        n = int(dur * x + 1e-9)
        billed = (n * 9.3 + (dur - n) * 6.0) / dur
        dur = int(round(dur * (billed - 1.3) / (5.0 - 1.3)))
        return dur, karl_bout(start, dur, "DiggingSpade")
    ev, prev = [], None
    run = int(dur * x + 1e-9)                              # the Running minutes close the bout, so the rate never steps down
    for i in range(dur):
        cls = "Running10kmh" if i >= dur - run else "HeavyWork"
        if cls != prev:
            ev.append({"minute": start + i, "kind": "activity", "rate": RATE[cls], "moving": True})
            prev = cls
    ev.append({"minute": start + dur, "kind": "activity", "rate": IDLE, "moving": False})
    return dur, ev


def karl_bout(start, dur, cls):
    return [{"minute": start, "kind": "activity", "rate": RATE[cls]},
            {"minute": start + dur, "kind": "activity", "rate": IDLE}]


def karl_events(arm, vigorous=True):
    """KARL_WARM sedentary days, then REST (one day) or three SUSOPS days; minute 0 is 00:00 of the first warm day.
    Returns (the events, the days, the morning walk's minutes)."""
    days = KARL_WARM + (1 if arm == "REST" else 3)
    rest_kcal = KARL_MJ["REST"] * KCAL_PER_MJ
    am_dur = karl_walk(0, KARL_AM[1], KARL_AM[2], vigorous)[0]
    ev = [{"minute": 0, "kind": "sleep", "asleep": True}]
    for d in range(days):
        base = d * 1440
        susops = arm != "REST" and d >= KARL_WARM
        kcal = KARL_MJ[arm] * KCAL_PER_MJ if susops else rest_kcal
        for hh in KARL_MEALS:
            ev.append({"minute": base + hh * 60, "kind": "eat", "vec": M.mixed(kcal / 3, water=300.0 * kcal / 1950)})
        after_susops = arm != "REST" and d - 1 >= KARL_WARM
        ev.append({"minute": base + (5 if after_susops else 6) * 60, "kind": "sleep", "asleep": False})
        if not susops:
            ev.append({"minute": base + KARL_NIGHT * 60, "kind": "sleep", "asleep": True})
            continue
        if d < days - 1:
            ev.append({"minute": base + 1440 + 60, "kind": "sleep", "asleep": True})        # 01:00
        ev += karl_walk(base + KARL_AM[0], KARL_AM[1], KARL_AM[2], vigorous)[1]
        ev += karl_walk(base + KARL_EVE[0], KARL_EVE[1], KARL_EVE[2], vigorous)[1]
        ev += karl_bout(base + KARL_PM[0], KARL_PM[1], "DiggingSpade")
        battery = max(KARL_BATTERY[0], KARL_AM[0] + am_dur + 4)       # after a longer morning walk
        ev += karl_bout(base + battery, KARL_BATTERY[1], "MediumWork")
    ev.sort(key=lambda e: e["minute"])
    return ev, days, am_dur


def karl_vas(day0, am_dur):
    """The day's 8 VAS rows: before and after each meal, before and after the morning walk."""
    out = []
    for hh in KARL_MEALS:
        out += [day0 + hh * 60 - 1, day0 + hh * 60]
    out += [day0 + KARL_AM[0] - 1, day0 + KARL_AM[0] + am_dur - 1]
    return sorted(out)


def karl_rows(arm, vigorous=True, paths=()):
    """(the server-path replay's per-minute rows of twin K's `arm`, its day count, the morning walk's minutes)."""
    ev, days, am_dur = karl_events(arm, vigorous)
    rows, _ = RL.replay_arm(ev, minutes=days * 1440, backend="server", start_age=0.0, paths=paths,
                            player={"weight": KARL_KG, "female": False}, rng="half")
    return rows, days, am_dur


def karl_k_arm(arm, vigorous=True):
    """(mean HUNGER at the VAS rows of the arm's study days, each study day's billed expenditure in MJ)."""
    rows, days, am_dur = karl_rows(arm, vigorous, ("body.eeDay",))
    reads = [rows[m]["HUNGER"] for d in range(KARL_WARM, days) for m in karl_vas(d * 1440, am_dur)]
    ee = [rows[d * 1440 + 1438]["body.eeDay"] / KCAL_PER_MJ for d in range(days)]   # the day's 1,440 steps
    return sum(reads) / len(reads), ee[KARL_WARM:]


def karl_k(vigorous=True):
    """Twin K: BAL % and DEF % against REST (Table 2's quantity), and the billed MJ per study day of each arm."""
    rest, ee_rest = karl_k_arm("REST")
    bal, ee_bal = karl_k_arm("BAL", vigorous)
    dfc, ee_def = karl_k_arm("DEF", vigorous)
    return {"bal": 100 * (bal / rest - 1), "dfc": 100 * (dfc / rest - 1), "rest": rest,
            "ee": {"REST": ee_rest, "BAL": ee_bal, "DEF": ee_def}}


def karl_pass(bal, dfc):
    """Each arm inside its band in the deficit registry (deficit_oracles.py, where the bands live): DEF within 1.5x of
    +26 % (17.3 to 39 %, the activity oracle's tolerance, spec section 5c, Plan 11c Task 4b, inside the study's own
    95 % CI -3 to 54) and BAL within -64 to -46 % (S1892, the band satiety carries it in since Plan 11g Task 6c; the
    1.5x band -82.5 to -36.7 until Plan 11g Task 7)."""
    from . import deficit_oracles as DO       # late: the registry imports this module
    return DO.BY_NAME["karl_bal"].margin(bal) >= 0, DO.BY_NAME["karl_def"].margin(dfc) >= 0


def test_karl_2021_as_the_paper_ran_it_on_the_server_path(host):
    # S1325: hunger -55 % (BAL) and +26 % (DEF, 95 % CI -3 to 54) against REST, each within 1.5x (karl_pass). Since the
    # refit (Plan 11f Task 2c fix 1) twin K read BAL -45.1 and DEF +30.2 on the P model, -45.8 and +30.0 under G's
    # provisional constants (Plan 11g Task 4), -44.7 and +29.9 under the gut stage's fit (Task 6), -52.7 and +30.4 under the refit meal pool M (Task 6c), -54.5 and +30.1 under its fix 1's refit, all inside (+30.3 before fix 2's EX_BYPASS_LO 0.282; -43.3 and +36.0 in Task 2c; at
    # 7500 / 1.0 -28.4 and +88.1, both outside). Under the deficit refit (Plan 11g Task 7, BAL a constraint in -64 to
    # -46 %, karl_pass): BAL -49.2 and DEF +30.4. DEF's days 2 and 3 carry a trailing deficit of about 2,270 kcal, 0.48
    # of the 24 h expenditure, past EX_BYPASS_HI 0.405, so the lag is bypassed whole (about 0.68 of the ramp at 0.575),
    # and the sleep factor's 1.18 from the 4 h nights; BAL's surplus excludes the lagged exercise share, so it reads a
    # large one. Under Plan 13 Task 12's lean partition at the day close BAL and DEF hold; DEF's expenditure reads 19.79, 19.90 and 19.78 MJ (19.88 and 19.75 before),
    # 0.72 over the doubly labelled water (0.71), BAL's day 3 20.03 (20.02). Under Plan 13 Task 10c's low-fat ramp DEF
    # reads +30.0 (BAL -49.2)
    k = karl_k()
    assert karl_pass(k["bal"], k["dfc"]) == (True, True), k
    assert (round(k["bal"], 1), round(k["dfc"], 1)) == (-49.2, 30.0), k
    # the calibration check against the doubly labelled water: the gap is a reading, never tuned
    assert [round(x, 2) for x in k["ee"]["DEF"]] == [19.79, 19.9, 19.78], k["ee"]
    assert [round(x, 2) for x in k["ee"]["BAL"]] == [19.79, 20.01, 20.03], k["ee"]
    assert round(sum(k["ee"]["DEF"]) / 3 - KARL_TDEE_MJ["DEF"], 2) == 0.72, k["ee"]
    assert round(sum(k["ee"]["BAL"]) / 3 - KARL_TDEE_MJ["BAL"], 2) == -0.06, k["ee"]
    assert round(k["ee"]["REST"][0], 2) == 9.06 and KARL_MJ["REST"] > k["ee"]["REST"][0], k["ee"]


def test_karl_2021_not_vigorous_overshoots_a_named_non_reproduction(host):
    # the same kcal billed under the vigour bar (the loaded walks at DiggingSpade, 5.0, for 121 and 233 min): no acute
    # suppression, so DEF overshoots, +41.5 against the band's 39, and BAL reads -45.8, 0.2 points short of S1892's -46
    # (the band karl_pass reads since Plan 11g Task 7; inside the 1.5x band before), under the deficit refit (Task 7; +41.1
    # and -51.4 under Task 6c fix 1's satiety refit; +41.0 and -49.7 under Task 6c's fit; +40.6 and -41.4 under the gut stage's fit, Task 6; +40.4 and -42.8 under G's provisional constants; +40.7 and -42.0 on the P model; +47.0 and -40.2 in Plan 11f
    # Task 2c). The writer's limitation names it:
    # heavy work the model does not class as vigorous overshoots the hunger rise of a heavy labour deficit (S1325)
    # Under Plan 13 Task 12's lean partition at the day close: DEF +41.6, BAL -45.8; under Task 10c's low-fat ramp DEF
    # +41.1, still over the 39 ceiling
    k = karl_k(vigorous=False)
    assert karl_pass(k["bal"], k["dfc"]) == (False, False), k
    assert (round(k["bal"], 1), round(k["dfc"], 1)) == (-45.8, 41.1), k
    assert [round(x, 2) for x in k["ee"]["DEF"]] == [19.79, 19.9, 19.78], k["ee"]      # the vigorous twin's kcal


# --- King 2011 at steady state (S1312) -----------------------------------------------------------------------------

KING_KG = 116.0                   # the stand-in whose idle day (awake 16 h) is the oracle's 2,500 kcal


def king_steady_server(host, bypass=None):
    """(the bout's minutes, each arm's late mean HUNGER); bypass (LO, HI) replaces the ramp's ends on each replay."""
    if bypass is not None:
        return with_bypass(bypass, lambda: king_steady_server(host))
    run_kcal = 4715.0 * A.KCAL_PER_KJ
    cut = 4820.0 * A.KCAL_PER_KJ / 2
    day = 1440
    bout = int(round(run_kcal / ex_per_min(host, "Running10kmh", KING_KG)))

    def arm(trim, run):
        ev = []
        for d in range(3):
            for hh in (2, 4.75, 11):
                kc = 2500.0 / 3 - (trim if d == 2 and hh in (2, 4.75) else 0.0)
                ev.append({"minute": d * day + int(hh * 60), "kind": "eat", "vec": M.mixed(kc)})
            ev.append({"minute": d * day + 900, "kind": "sleep", "asleep": True})       # 23:00
            ev.append({"minute": d * day + 1380, "kind": "sleep", "asleep": False})     # 07:00
        if run:
            ev.append({"minute": 2 * day, "kind": "activity", "rate": RATE["Running10kmh"]})
            ev.append({"minute": 2 * day + bout, "kind": "activity", "rate": IDLE})
        ev.sort(key=lambda e: e["minute"])
        rows, _ = RL.replay_arm(ev, minutes=3 * day + 480, backend="server", start_age=8.0,
                                player={"weight": KING_KG, "female": False}, rng="half")
        late = [r["HUNGER"] for r in rows[2 * day + 180:2 * day + 480]]
        return sum(late) / len(late)

    return bout, {"control": arm(0.0, False), "restriction": arm(cut, False), "exercise": arm(0.0, True)}


def test_king_2011_at_steady_state_on_the_server_path(host):
    # S1312: exercise within a quarter of the restriction's rise and under 3.3 mm of control (Plan 11c Task 4b's band);
    # since the refit (Plan 11f Task 2c fix 1) the rise read 0.0906 and the distance 0.92 mm on the P model, 0.0863 and
    # 0.92 mm under G's provisional constants (Plan 11g Task 4), 0.0995 and 0.98 mm under the gut stage's fit (Task 6), 0.0916 and 0.92 mm under the refit M (Task 6c), 0.0947 and 0.94 mm under its fix 1's refit, 0.0944 and 0.94 mm under its fix 2's, 0.091 and 1.01 mm under the deficit refit (Plan 11g Task 7), 0.091 and 1.24 mm with EX_BYPASS_HI at mid-plateau (its fix 1, the READ below) (0.96 before fix 2's EX_BYPASS_LO 0.282; 0.089 and 0.62 mm in
    # Task 2c, 0.1043 and 2.43 mm at 7500 / 1.0)
    assert abs(idle_day(host, KING_KG, 16) - 2500.0) < 2.0
    bout, k = king_steady_server(host)
    rise = k["restriction"] - k["control"]
    band = abs(k["exercise"] - k["control"])
    assert bout == 73
    assert rise > 0.02 and band < 0.25 * rise and band * A.MM_PER_HUNGER < 3.3, k
    assert (round(rise, 4), round(band * A.MM_PER_HUNGER, 2)) == READ["king"], (rise, band * A.MM_PER_HUNGER)


def with_bypass(bypass, fn):
    """fn() with every server replay built inside it reading K.deficit.EX_BYPASS_LO and EX_BYPASS_HI = bypass."""
    init = RL.ServerReplay.__init__

    def patched(self, *a, **kw):
        init(self, *a, **kw)
        self.K.deficit.EX_BYPASS_LO, self.K.deficit.EX_BYPASS_HI = bypass

    RL.ServerReplay.__init__ = patched
    try:
        return fn()
    finally:
        RL.ServerReplay.__init__ = init


STEP = (0.25, 0.25 + 1e-12)       # ruling 11c-32 as first written: the whole lag bypassed from a 25 % deficit on
NO_BYPASS = (5.0, 6.0)            # a share no day reaches


def test_king_2011_the_ramp_holds_the_band_a_25_percent_step_leaves(host):
    # ruling 11c-32 as amended: the bypass is a ramp because a 25 % step breaks King 2011 at steady state (S1312:
    # intake stays with control; S1318: Whybrow's 26-28 % arms compensate). On the server path (Plan 11f Task 2c fix 1)
    # the step lifted the exercise arm 6.70 mm over control on the P model, past both a quarter of the restriction's rise
    # (5.89 mm) and 3.3 mm, where the ramp read 0.92 mm and no bypass 0.29 mm; under G's provisional constants (Plan 11g
    # Task 4) 6.66 mm against a quarter rise of 5.61 mm, the ramp 0.92 mm and no bypass 0.29 mm; under the deficit
    # refit (Plan 11g Task 7) READ's king_step and king_nobypass: the step lifts 4.6 mm, past the band's bound
    # min(3.3 mm, a quarter of the rise, 5.92 mm), though no longer past the quarter rise, and the ramp holds 1.24 mm
    # (1.01 mm at Task 7's EX_BYPASS_HI 0.44);
    # the ramp only ever raises the lag's share
    _, ramp = king_steady_server(host)
    _, step = king_steady_server(host, STEP)
    _, none = king_steady_server(host, NO_BYPASS)
    assert step["control"] == ramp["control"] and step["restriction"] == ramp["restriction"]   # no exercise, no bypass
    rise = ramp["restriction"] - ramp["control"]
    lift = step["exercise"] - step["control"]
    assert lift * A.MM_PER_HUNGER >= min(3.3, 0.25 * rise * A.MM_PER_HUNGER), (lift, rise)        # the step leaves the band
    assert none["exercise"] <= ramp["exercise"] < step["exercise"], (none, ramp, step)
    assert round(lift * A.MM_PER_HUNGER, 2) == READ["king_step"], lift
    assert round((none["exercise"] - none["control"]) * A.MM_PER_HUNGER, 2) == READ["king_nobypass"], none


def test_karl_2021_the_ramp_passes_where_no_bypass_fails_and_a_25_percent_step_now_passes(host):
    # the contrast the King test draws, on twin K (S1325): at the chosen ramp both arms pass; with no bypass DEF reads
    # +9.0 and fails the 17.3 floor of the 1.5x band; with a 25 % step it read +43.6 and failed the 39 ceiling (Plan 11f
    # Task 2c fix 2; the contrast was unpinned after the fit-1 deletion of the simplified Karl test); under G's
    # provisional constants (Plan 11g Task 4) +8.8 and +43.5; under the gut stage's fit (Task 6) +8.8 and +43.4; under
    # the refit M (Task 6c) +9.2 and +43.8; under its fix 1's refit +8.9 and +43.5. A NAMED NON-REPRODUCTION since the
    # deficit refit (Plan 11g Task 7): no bypass reads +8.0 and still fails, but the step reads +31.8, inside the band:
    # the wider span (3970.55) lowers every arm's rise, and the ramp, now 0.282 to 0.405, bypasses Karl's DEF days (a
    # 24-h deficit share of about 0.48) whole as the step does (the ramp +30.4); the ramp's case rests on King 2011 alone
    # (test_king_2011_the_ramp_holds_the_band_a_25_percent_step_leaves). Under Plan 13 Task 12's lean partition at the day close the step reads +31.9;
    # under Task 10c's low-fat ramp no bypass +7.6 and the step +31.4
    ramp = karl_k()
    none = with_bypass(NO_BYPASS, karl_k)
    step = with_bypass(STEP, karl_k)
    assert karl_pass(ramp["bal"], ramp["dfc"]) == (True, True), ramp
    assert karl_pass(none["bal"], none["dfc"])[1] is False and none["dfc"] < 17.3, none
    assert karl_pass(step["bal"], step["dfc"]) == (True, True) and ramp["dfc"] <= step["dfc"] < 39.0, step
    assert (round(none["dfc"], 1), round(step["dfc"], 1)) == (7.6, 31.4), (none["dfc"], step["dfc"])


# --- the lag: Whybrow 2008 (S1318) and E-MECHANIC (S1320, S1664) ---------------------------------------------------

def lag_run(w, cls, bout_min, days, dtM, meal_kcal):
    spd = 1440 // dtM
    ev = []
    for d in range(days):
        ev.append({"minute": d * spd + 120 // dtM, "kind": "activity", "rate": RATE[cls]})
        ev.append({"minute": d * spd + (120 + bout_min) // dtM, "kind": "activity", "rate": IDLE})
        for h in M.FAST_MEAL_H:
            ev.append({"minute": int(d * spd + h * 60 // dtM), "kind": "meal", "size": meal_kcal})
    ev.sort(key=lambda e: e["minute"])
    return RL.replay_arm(ev, minutes=days * spd, dtM=dtM, backend="server", paths=("satiety.L", "body.exKcalDay"),
                         player={"weight": w, "female": False}, rng="half")


def lag_shares(rows, be, days, dtM, bout_min, from_day):
    """lagged(record.satiety.L) over the day's bout kcal at each step from day from_day on, and the bout kcal."""
    spd = 1440 // dtM
    a, b = 120 // dtM - 1, (120 + bout_min) // dtM - 1
    k = [rows[d * spd + b]["body.exKcalDay"] - rows[d * spd + a]["body.exKcalDay"] for d in range(days)]
    out = [be.K.deficit.lagged(rows[i]["satiety.L"]) / k[i // spd] for i in range(from_day * spd, days * spd)]
    return out, k


def whybrow_server(host, mj):
    kcal = mj * 1000 * A.KCAL_PER_KJ
    bout = int(round(kcal / ex_per_min(host, "Running15kmh", 70.0)))
    rows, be = lag_run(70.0, "Running15kmh", bout, 16, 1, (idle_day(host, 70.0, 24) + kcal) / 3)
    shares, k = lag_shares(rows, be, 16, 1, bout, 2)
    return bout, sum(shares) / len(shares), lag_shares(rows, be, 1, 1, bout, 0)[0][-1]


def e_mechanic_server(host, cls, weeks=(24, 48)):
    """The mean share over the last week of each of `weeks`, read off one run to the last."""
    last = weeks[-1]
    rows, be = lag_run(90.0, cls, 60, last * 7, 30, (idle_day(host, 90.0, 24) + ex_per_min(host, cls, 90.0) * 60) / 3)
    out = []
    for wk in weeks:
        shares, _ = lag_shares(rows[:wk * 7 * 48], be, wk * 7, 30, 60, wk * 7 - 7)
        out.append(sum(shares) / len(shares))
    return out


def test_whybrow_on_the_server_path(host):
    # S1318: about 30 % over days 3-16 within 1.5x at both doses; about 0 the same day. The oracle reads 0.2984 and
    # day 1 0.0414; the server's lag is the same kernel stepped on the billed exercise kcal. Under Plan 13 Task 12's lean partition at the day close the low dose's
    # share reads 0.2988 (0.2987 before)
    hi, lo = whybrow_server(host, 3.5), whybrow_server(host, 1.75)
    for bout, share, day1 in (hi, lo):
        assert max(share / 0.30, 0.30 / share) <= A.TOL and day1 < 0.05, (bout, share, day1)
    assert (hi[0], round(hi[1], 4), round(hi[2], 4)) == (53, 0.2985, 0.0414), hi
    assert (lo[0], round(lo[1], 4), round(lo[2], 4)) == (27, 0.2988, 0.0413), lo


def test_e_mechanic_on_the_server_path(host):
    # S1320 with S1664: 0.53-0.89 at 24 weeks at both doses, plateaued (week 24 within 1 % of week 48); the oracle 0.69998
    for cls in ("MediumWork", "UsingTools"):
        share, later = e_mechanic_server(host, cls)
        assert 0.53 <= share <= 0.89 and abs(share / later - 1) <= 0.01, (cls, share, later)
        assert round(share, 4) == 0.7 and round(later, 4) == 0.7, (cls, share, later)


# --- S1255: a 25 % deficit -----------------------------------------------------------------------------------------

def deficit_server(host, days=7):
    """The 70 kg man at 75 % of his maintenance (three equal meals) for `days` after one maintenance day; the mean es
    over the last day and its request-level rise in mm (ruling 11c-31's 260 mm a unit)."""
    ev = sleep_events(days + 1)
    for d in range(days + 1):
        for h in M.FAST_MEAL_H:
            ev.append({"minute": int(d * 1440 + h * 60), "kind": "meal", "size": "maint" if d == 0 else 0.75 * 1948.7298 / 3})
    ev.sort(key=lambda e: e["minute"])
    rows, _ = RL.replay_arm(ev, minutes=(days + 1) * 1440, backend="server", paths=("body.energyState",), **MAN)
    es = [r["body.energyState"] for r in rows[days * 1440:]]
    e = sum(es) / len(es)
    rise = host.call("deficit.hungerTarget", 1 - M.H_REQ, e) - host.call("deficit.hungerTarget", 1 - M.H_REQ, 1)
    return e, rise * M.MM_PER_HUNGER


def test_a_25_percent_deficit_on_the_server_path(host):
    # S1255 (CALERIE 2: < 10 mm over 2 y at a 25 % deficit): the 70 kg man's quarter deficit (-487 kcal) on the
    # pipeline, a week in, reads es 1.0777 and 5.1 mm at the request since the deficit refit (Plan 11g Task 7; es 1.0947
    # and 6.7 mm in Plan 11f Task 2c fix 1, 5.9 mm in its Task 2c), reproduced; at 7500 / 1.0 it read 16.0 mm, and the
    # deleted arithmetic oracle 13.5 mm on a 2,500 kcal day
    e, mm = deficit_server(host)
    assert mm < 10, (e, mm)
    assert (round(e, 4), round(mm, 1)) == READ["s1255"], (e, mm)


# --- S1254: the fat drive, ad-libitum intake per kg of fat lost (Plan 13 Task 10c) -----------------------------------

S1254_DEP = (0.25, 0.40, 0.55)    # the fat depletions read, inside the ramp's linear part (FAT_DEP_LO 0.10 to HI 0.70)
S1254_LOW = 0.05                  # a depletion below FAT_DEP_LO: the soft threshold reads nothing there
S1254_DAYS = 5                    # day 0 at maintenance (fills the window), days 1-4 eaten at the request
S1254_READ = (2, 3, 4)            # the days read: day 1 carries the first day's catch-up


def fat_loss_intake(host, dep, days=S1254_DAYS):
    """The reference (no-trait) body, its fat set fmRef x (1 - dep) at minute 2 (fmRef kept), eating three meals at
    maintenance on day 0 and at the request after (ad libitum, the steady eater's protocol), asleep 23:00-07:00: the
    mean intake over S1254_READ, kcal/d, and the fat lost, kg. The reduced body's own maintenance sizes day 0."""
    fm_ref = host.call("body.create", None, None, host.K.strength.DEFAULTS, 1)["fm"]
    ev = sleep_events(days)
    ev.append({"minute": 2, "kind": "setpath", "path": "body.fm", "value": fm_ref * (1 - dep)})
    for d in range(days):
        for h in M.FAST_MEAL_H:
            ev.append({"minute": int(d * 1440 + h * 60), "kind": "meal", "size": "maint" if d == 0 else "request"})
    ev.sort(key=lambda e: e["minute"])
    _, be = RL.replay_arm(ev, minutes=days * 1440, backend="server", player={"female": False}, rng="half")
    by = RL.intake_by_day(be.eats)
    return sum(by[d] for d in S1254_READ) / len(S1254_READ), fm_ref * dep


def fat_loss_server(host):
    """S1254's reading on the server path: the intake at no loss (base), below the ramp (low) and at each S1254_DEP;
    the least-squares slope of intake on the kg of fat lost over S1254_DEP (kcal/d per kg of fat) and the two consecutive pairs'."""
    base, _ = fat_loss_intake(host, 0.0)
    low, _ = fat_loss_intake(host, S1254_LOW)
    pts = [fat_loss_intake(host, d) for d in S1254_DEP]
    xs, ys = [p[1] for p in pts], [p[0] for p in pts]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    pairs = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(len(xs) - 1)]
    return {"base": base, "low": low, "kg": xs, "intake": ys, "slope": slope, "pairs": pairs}


def test_s1254_the_fat_drive_on_the_server_path(host):
    # S1254 (Polidori 2016: about 100 kcal/d more intake per kg of WEIGHT lost, k_P 95 in its model, S2208) read per kg
    # of FAT lost against 95 / 0.76 = 125 (the Forbes fat share the model assumes, S2206; deficit_oracles' header;
    # Plan 13 Task 10c fix 2) within 1.5x, on the reference body at three fat depletions inside the low-fat hunger
    # ramp's linear part (Plan 13 Task 10c), and the registry's stability checks: the pairs within 2x, none flat,
    # nothing below FAT_DEP_LO
    from . import deficit_oracles as DO
    r = {"s1254": fat_loss_server(host)}
    for n in ("s1254", "s1254_linear", "s1254_flat", "s1254_low"):
        assert DO.BY_NAME[n].margin(DO.BY_NAME[n].pick(r)) >= 0, (n, r)
    f = r["s1254"]
    assert (round(f["slope"], 1), [round(x, 1) for x in f["pairs"]], round(f["low"] - f["base"], 1)) == READ["s1254"], f
    assert DO.BY_NAME["s1254"].margin(DO.BY_NAME["s1254"].pick(r)) >= 0.9, f   # the fit sits within ~4 % of 125


# the readings the tests above pin that their own lines do not spell out (each at the deficit refit's constants, Plan
# 11g Task 7)
READ = {
    "lowcarb_g": (1.0, 1.0, 0.967),     # g: the mixed arm at 08:00 and 20:00 of day 1, the low arm at 20:00 (the simplified path 0.951)
    "lowcarb_des": 0.0,                 # the low arm's es less the mixed arm's at 20:00
    "king": (0.091, 1.24),              # the restriction's late rise and exercise's distance in mm with EX_BYPASS_HI at mid-plateau (Plan 11g Task 7 fix 1, ruling T7-6; 0.091 and 1.01 under Task 7's 0.44; 0.0944 and 0.94 under Task 6c fix 2's satiety refit; 0.0947 and 0.94 under fix 1's; 0.0916 and 0.92 under Task 6c's fit; 0.0995 and 0.98 under the gut stage's fit, Task 6; 0.0863 and 0.92 under its provisional constants, Task 4; 0.0906 and 0.92 on the P model, 0.089 and 0.62 in Task 2c, 0.1043 and 2.43 at 7500 / 1.0)
    "king_step": 4.6,                   # a 25 % step's exercise arm over control, mm, under the deficit refit (Plan 11g Task 7; 6.83 under Task 6c fix 2's; 6.82 under fix 1's; 6.7 under Task 6c's fit; 7.09 under the gut stage's fit, Task 6; 6.66 under its provisional constants; 6.70 on the P model, Plan 11f Task 2c fix 1)
    "king_nobypass": 0.2,               # no bypass's, mm, under the deficit refit (Plan 11g Task 7; 0.29 under Task 6c fix 2 and fix 1, as under Task 6c's fit; 0.3 under the gut stage's fit, 0.29 under its provisional constants)
    "s1254": (125.3, [124.9, 125.6], -1.0),   # the slope, kcal/d per kg of fat, the pair slopes and low less base at FAT_GAIN 0.651709 (Plan 13 Task 10c fix 2; 101.0, [100.6, 101.4] at Task 10c's 0.524404; 96.3 at 0.5)
    "s1255": (1.0599, 3.9),             # es over day 7 and its rise at the request, mm, under Plan 13 Task 10c's low-fat ramp (1.0739 and 4.8 under Task 12's lean partition at the day close; 1.0777 and 5.1 under the deficit refit, Plan 11g Task 7; 1.0947 and 6.7 in Plan 11f Task 2c fix 1, 1.09 and 5.9 in its Task 2c, 1.0492 and 16.0 at 7500 / 1.0)
}


def test_karl_2021_over_twin_k_five_billings_the_fit_ranks_by(host):
    # Plan 11g Task 7: deficit_oracles.karl, the worst case the deficit drive's fit scores Karl's DEF arm at (Plan 11f
    # ruling 2c-1): the loaded walks billed whole at ClimbRope, at Running10kmh or as loaded Walking5kmh (33.5 kg of 50),
    # and the day without the task battery, beside the as-built twin; every billing passes both arms (BAL inside S1892's
    # -64 to -46 %, DEF within 1.5x of +26 %). ClimbRope sets the smallest scored margin (+33.7 toward the 39 ceiling,
    # 0.492 of a half-width) and the loaded walk holds EX_BYPASS_HI from above (+25.8 at 0.405, Task 7 fix 1's
    # mid-plateau; +22.8 at Task 7's 0.44, +21.9 at 0.45). Under Plan 13 Task 12's lean partition at the day close: run10 +32.9, the loaded walk +25.7, no battery
    # +29.5, ClimbRope's margin 0.487. Under Task 10c's low-fat ramp: as built +30.0, ClimbRope +33.2, run10 +32.4, the
    # loaded walk +25.2, no battery +29.0, ClimbRope's margin 0.531 (fast_r2's 0.468 is now the smallest scored margin)
    from . import deficit_oracles as DO
    k = DO.karl(host)
    for alt, r in k.items():
        assert karl_pass(r["bal"], r["dfc"]) == (True, True), (alt, r)
    assert {a: (round(r["bal"], 1), round(r["dfc"], 1)) for a, r in k.items()} == {
        "asbuilt": (-49.2, 30.0), "climb": (-48.4, 33.2), "run10": (-49.1, 32.4), "loadwalk": (-49.4, 25.2),
        "nobattery": (-49.3, 29.0)}, k
    assert round(DO.BY_NAME["karl_def"].margin(DO.BY_NAME["karl_def"].pick({"karl": k})), 3) == 0.531, k


# --- the energy moodle over a resting fast (Plan 11g Task 7 fix 1, ruling T7-2) ----------------------------------------

FAST_SIG = "_G.NutritionRevamp.server.bus.lastSig.admin"      # the bus's signature, the level the push is keyed on


def long_fast_levels(player, fast_days=6):
    """A sedentary fast on the server path: the warm maintenance days and protocol day 0's three meals, then nothing
    for fast_days days. Returns (the bus's energy level, the plain rung of es, es) at each minute from the last meal."""
    plan = M.warm()
    plan.update(M.meals_of(0, "maint"))
    last = max(plan)
    days = M.FAST_WARM_DAYS + 1 + fast_days
    ev = sleep_events(days) + [{"minute": m, "kind": "meal", "size": k} for m, k in sorted(plan.items())]
    ev.sort(key=lambda e: e["minute"])
    rows, be = RL.replay_arm(ev, minutes=days * 1440, backend="server", paths=("body.energyState", FAST_SIG),
                             player=player, rng="half", sex_specific=True)
    at = [be.K.view.ENERGY_AT[i] for i in range(1, 5)]
    bus = [int(r[FAST_SIG] // 1000) % 10 for r in rows[last:]]
    es = [r["body.energyState"] for r in rows[last:]]
    plain = [sum(1 for a in at if e >= a) for e in es]
    return bus, plain, es


def deepest_held_fall(bus, es):
    """The deepest es under the bound of a level the bus holds (0 when no level is held under its bound)."""
    at = (1.10, 1.25, 1.40, 1.55)
    return max([at[b - 1] - e for b, e in zip(bus, es) if b >= 1] + [0.0])


def largest_drawdown(es, after_min=1440):
    """The largest fall of es under its running peak from after_min minutes after the last meal on."""
    peak, fall = es[after_min], 0.0
    for e in es[after_min:]:
        peak = max(peak, e)
        fall = max(fall, peak - e)
    return fall


def level_changes(levels):
    """[(level, hours from the last meal)] at each change."""
    out = []
    for i in range(1, len(levels)):
        if levels[i] != levels[i - 1]:
            out.append((levels[i], round(i / 60.0, 1)))
    return out


def test_a_sedentary_fast_never_steps_an_energy_level_down(host):
    # ruling T7-2: the energy moodle never flickers in a resting fast. The plain rung did: the 70 kg man's es plateaus
    # at 1.2456, 0.0044 under level 2's 1.25, and its slow daily sawtooth (its largest fall under the running peak from
    # 24 h on 0.00234, pinned below) crossed 1.25 at 52.0 h, back at 67.6 h and again at 76.0 h. The bus now holds a
    # reached level until es falls ENERGY_BAND (0.01) under its bound (K.view.energyLevel, a game choice), and the
    # mirror carries that held level to the client (ruling T7-7), so over six days of fasting no body steps a level
    # down; the deepest es under a held level's bound is the man's 0.00092. Level 1 stays about 18 h after the last
    # meal (ruling 9d-2: 18.1 h for the man, 17 h at the 3,100 kcal span); level 2 comes at 52.0 h for the man and from
    # the plateau alone at 27.1 h for the 100 kg man, and the 50 and 60 kg women stay at level 1 (es 1.201 and 1.223 at
    # six days). A threshold move instead (ENERGY_AT[2] under the man's plateau) was rejected: a plateau sits wherever a
    # body's expenditure puts it (es 1.1904, 1.2118, 1.2482 and 1.2901 at 48 h for the 50 and 60 kg women and the 70
    # and 100 kg men, pinned below), so a bound inside that range meets some body's sawtooth. Under Plan 13 Task 12's lean partition at the day close the plain rung
    # steps back at 66.3 h (67.6 before), the man's deepest fall under a held bound reads 0.00105 (0.00092), and es at
    # 48 h and six days 1.2117 and 1.2229, 1.2481 and 1.2562, 1.2897 and 1.3049 for the 60 kg woman and the 70 and
    # 100 kg men. Plan 13 Task 10c's low-fat ramp: a six-day fast depletes under FAT_DEP_LO (0.10), so the fat term
    # no longer lifts es and es now falls slowly after its plateau as adaptive thermogenesis lowers the deficit. The
    # 70 kg man stays at level 1 (es 1.2438 at 48 h, 1.234 at six days); the flicker the band removes is now the 74 kg
    # man's (the plain rung back at 63.2 h), whose deepest fall under a held bound is 0.008; the largest fall under
    # es's running peak is the 70 kg man's 0.01124, above the old ENERGY_BAND 0.01, and a 73 kg man held level 2 by
    # 0.00003 (0.00997 under its bound; a reading, not pinned). Task 10c fix 1: men from 72.56 kg stepped 2 to 1 late in
    # day 6 at 0.01 (the 72.6 kg man, pinned here, falls 0.01076 under the bound), so ENERGY_BAND is 0.035 (the long
    # fast's deepest fall, test_a_long_sedentary_fast_never_steps_an_energy_level_down)
    want = {(50.0, True): [(1, 19.4)], (60.0, True): [(1, 18.8)], (70.0, False): [(1, 18.2)],
            (72.6, False): [(1, 18.1), (2, 30.6)], (74.0, False): [(1, 18.1), (2, 29.6)],
            (100.0, False): [(1, 17.7), (2, 27.2)]}
    got = {}
    for (w, female), changes in want.items():
        bus, plain, es = long_fast_levels({"weight": w, "female": female})
        assert all(b >= a for a, b in zip(bus, bus[1:])), (w, female, level_changes(bus))
        assert level_changes(bus) == changes, (w, female, level_changes(bus))
        if w == 74.0:
            assert level_changes(plain) == [(1, 18.1), (2, 29.6), (1, 63.2)]   # the flicker the band removes
        got[(w, female)] = (round(deepest_held_fall(bus, es), 5), round(largest_drawdown(es), 5),
                            round(es[48 * 60], 4), round(es[-1], 4))
    # per body: the deepest es under a held level's bound, the largest fall under es's running peak from 24 h on, and
    # es at 48 h and at six days, ENERGY_BAND's evidence (its label cites these)
    assert got == {(50.0, True): (0.0, 0.00844, 1.1864, 1.1792), (60.0, True): (0.0, 0.00769, 1.2078, 1.2011),
                   (70.0, False): (0.0, 0.01124, 1.2438, 1.234), (72.6, False): (0.01076, 0.01087, 1.2487, 1.2392),
                   (74.0, False): (0.008, 0.01065, 1.2513, 1.242),
                   (100.0, False): (0.0, 0.00295, 1.286, 1.2833)}, got


def test_a_long_sedentary_fast_never_steps_an_energy_level_down(host):
    # Plan 13 Task 10c fix 1 (ruling T7-2, ENERGY_BAND re-ruled to 0.035): under the low-fat ramp es keeps falling
    # after a resting fast's plateau until the fat depletion passes FAT_DEP_LO (about 364 h), so the band must hold a
    # long fast's deepest fall, not six days'. The 72.6 kg man just reaches level 2 (es peaks at 1.25011) and by day 16
    # his es sits 0.03055 under its bound; at the old band 0.01 he stepped 2 to 1 late in day 6 (the Task 10c review's
    # sweep: 0.0307 at 72.55 kg was the deepest over 20-day fasts, so 0.031 is the floor)
    bus, plain, es = long_fast_levels({"weight": 72.6, "female": False}, fast_days=16)
    assert all(b >= a for a, b in zip(bus, bus[1:])), level_changes(bus)
    assert level_changes(bus) == [(1, 18.1), (2, 30.6)], level_changes(bus)
    assert level_changes(plain) == [(1, 18.1), (2, 30.6), (1, 32.9)]       # the step-down the band holds
    assert (round(deepest_held_fall(bus, es), 5), round(max(es), 5)) == (0.03055, 1.25011)
