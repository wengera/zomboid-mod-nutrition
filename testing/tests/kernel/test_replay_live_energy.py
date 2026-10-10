"""The energy and exercise-lag oracles on the shipped server pipeline (Plan 11f Task 2b, ruling F1-2): a server-path
twin of each, through tools/replay_live.py's server backend (ServerReplay: the mod's own adapters in their ORDER on the
golden stand-ins), on the oracle's own body and events as far as the server can take them. Each reading is pinned as a
READING, with its distance from the oracle's pin and from its study's band; grading stays on the oracles
(test_satiety_meal_studies.py, test_satiety_activity.py) until Task 2b's ruling.

What the server path adds to every oracle: an eat reaches the trailing-24 h window only as the stomach empties
(ctx.absorbed), the day partition moves fm and lm (fatDep enters the energy state), adaptive thermogenesis and the
training close run, and the expenditure is billed off the stand-in's metabolic rate by class (K.energy.classOf, the
Compendium bill), never injected. The stand-in idles at the engine's Default class (1.5, billed 1.3, standing quietly).

The twins, and where each departs from its oracle (each departure a choice named here):
- The 36 h fast, the steady eater, six meals against three (live) and the low-carbohydrate day: the oracles' own event
  lists on the 70 kg man (male, responder 1), asleep 23:00-07:00, as test_replay_live_oracle.py runs them. Six against
  three's warm-up eats fill the stomach and the pool too (the server has no energy-only eat). Six against three held is
  the satiety replay at the energy state 1 (kinetics and the writer alone, no body), from P 0 at 08:00.
- Karl 2021 (S1325): the oracle's body spends a flat 2,700 kcal a day (ASSUMED) and works 9.6 MJ a day (the study's)
  evenly over 8 h, vigorous every minute. The server cannot hold all three: its vigour needs a billed MET of 6.0 or
  more (W.vigorous), and its exercise kcal is (MET - 1.3) x mass a minute. Four twins, each matching two of the three:
    E   expenditure-matched: the stand-in's weight set so its idle day is 2,700 kcal (119.1 kg, awake 20 h); HeavyWork
        (engine 6.0, billed 6.0, vigorous) for the first 31 minutes of each work hour, 9.6 MJ a day;
    Env the same body and work at MediumWork (engine 3.9, billed 4.0, never vigorous), 54 minutes an hour;
    V   the 70 kg man (his own idle day, 2,032.7 kcal) doing the study's 9.6 MJ at HeavyWork, 52 minutes an hour;
    C   a 61 kg man at HeavyWork every work minute (vigorous throughout), which bills the study's 9.6 MJ; his own idle
        day.
  Each twin: one sedentary balanced day first (the study's; it fills the window and seeds the pool), then 72 h from
  06:00, meals at 07:00, 12:00 and 18:00 (the oracle's), asleep 02:00-06:00, BAL at 1.18 and DEF at 0.57 of the
  twin's own work-day expenditure; the reading is the mean written HUNGER over the protocol's awake minutes, against
  REST's. Karl's DEF reading spans 10 % to 66 % across them at the shipped constants: the twin's body, which no row
  gives, sets it.
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
- S1255: the oracle is K.energy.state's arithmetic, path-independent; its twin here is the 70 kg man eating 75 % of
  his maintenance for a week, the request-level rise read off the energy state the pipeline stamps on day 7.
Only `host`; no `parametrize`.
"""
import os
import sys

from . import test_satiety_activity as A
from . import test_satiety_meal_studies as M
from .server_host import REPO
from .test_replay_live_oracle import energy_run, fast_plans, meal_events, sleep_events

sys.path.insert(0, os.path.join(REPO, "tools"))
import replay_live as RL  # noqa: E402

MAN = {"player": {"weight": 70.0, "female": False}, "rng": "half"}
RATE = {"HeavyWork": 6.0, "MediumWork": 3.9, "UsingTools": 2.5, "Running10kmh": 6.9, "Running15kmh": 9.5}
IDLE = 1.5                        # the engine's Default class (a live idle player, #2875)


def ex_per_min(host, cls, w):
    """The exercise kcal a minute at class cls for a w kg stand-in: the billed MET above the idle class x mass / 60."""
    return (host.K.energy.COMPENDIUM[cls] - host.K.energy.COMPENDIUM.Default) * w / 60.0


def idle_day(host, w, awake_h):
    """A w kg man's idle day: REE off his birth lean mass plus the Default class's bill above rest while awake."""
    b = host.K.body.new(w, 1, host.rt.table(), 5, 1, 1, 0)
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
             "satiety": {"P": 0.0, "S": 0, "L": 0, "t": a0}}
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
    # S1613 (1.20, the oracle's 1.1x band 1.091-1.32) and S1614 (1.0): day 2 reads 1.342 (1.118x, outside the band; the
    # oracle 1.304, 1.087x), day 3 0.974 (the oracle 0.986); the fed arm 1,965 and 1,940 kcal (the oracle 1,963 and
    # 1,937), the fast arm 2,637 (2,560). The es log at 12, 24 and 36 h of the fast reads 1.001, 1.087 and 1.134
    # (the oracle 1.0, 1.087, 1.13: the stomach and fatDep), eb24 -1, -1300 and -1945 (-1, -1301, -1950) and g 1.0,
    # 0.946 and 0.766 (the oracle 1.0, 0.923, 0.741: the stomach's slower carbohydrate)
    f = fast_server()
    assert (round(f["r2"], 3), round(f["r3"], 3)) == (1.342, 0.974), f
    assert round(M.ratio(f["r2"], 1.20), 3) == 1.118 and M.ratio(f["r2"], 1.20) > M.TOL, f
    assert M.ratio(f["r3"], 1.0) <= M.TOL, f
    assert [round(x) for x in f["fed"]] == [1965, 1940] and round(f["fast"]) == 2637, f
    assert [round(x["body.energyState"], 3) for x in f["log"]] == [1.001, 1.087, 1.134], f
    assert [round(x["body.eb24"]) for x in f["log"]] == [-1, -1300, -1945], f
    assert [round(x["acute.g"], 3) for x in f["log"]] == [1.0, 0.946, 0.766], f


def test_the_steady_eater_on_the_server_path(host):
    # STEADY_TOL 0.03: days 2-4 at 1.0083, 0.9956 and 1.0007 x maintenance (the oracle 1.0075, 0.994, 0.9978), es 1.0007
    # to 1.0011 over day 5 (1.0004 to 1.0005): the 20:00 dinner empties after midnight into the hour-slotted window
    ratios, es = steady_server()
    assert all(abs(r - 1) <= M.STEADY_TOL for r in ratios) and all(abs(e - 1) <= M.STEADY_TOL for e in es)
    assert [round(r, 4) for r in ratios] == [1.0083, 0.9956, 1.0007], ratios
    assert (round(min(es), 4), round(max(es), 4)) == (1.0007, 1.0011), es


def test_six_meals_against_three_on_the_server_path(host):
    # [0.9, 1.3] (ruling 11d-3): held at es 1 the server's satiety path is the oracle's to 1e-12 (0.969); live it reads
    # 0.987 (the oracle 0.994: the warm-up eats fill the stomach and the pool on the server)
    held = six_held_sum(6, 150) / six_held_sum(3, 300)
    live = six_live_sum(6, 150) / six_live_sum(3, 300)
    assert abs(held - M.meal_frequency_ratio(host)) < 1e-12 and round(held, 3) == 0.969, held
    assert 0.9 <= live <= 1.3 and round(live, 3) == 0.987, live


def test_the_low_carbohydrate_day_on_the_server_path(host):
    # C9: the low arm runs g down at 20:00 of day 1 (0.967; the oracle 0.951), and at equal intake the two arms read the
    # same es on the server as on the oracle (ruling T4-1: g does not enter the energy state)
    m8, m20, low = lowcarb_server()
    assert round(m8["acute.g"], 3) == READ["lowcarb_g"][0] and round(m20["acute.g"], 3) == READ["lowcarb_g"][1], (m8, m20)
    assert round(low["acute.g"], 3) == READ["lowcarb_g"][2], low
    assert round(low["body.energyState"] - m20["body.energyState"], 4) == READ["lowcarb_des"], (low, m20)


# --- Karl 2021 (S1325) ---------------------------------------------------------------------------------------------

def karl_arm(host, intake, rest_kcal, work, w, per_hour, cls):
    """One arm: the sedentary balanced day, then 72 h from 06:00; the mean written HUNGER over the protocol's awake
    minutes."""
    ev = []
    for d in range(4):
        ink = rest_kcal if d == 0 else intake
        for hh in (7, 12, 18):
            ev.append({"minute": d * 1440 + (hh - 6) * 60, "kind": "eat",
                       "vec": M.mixed(ink / 3, water=300.0 * ink / 1950)})
        ev.append({"minute": d * 1440 + 1200, "kind": "sleep", "asleep": True})            # 02:00
        if d < 3:
            ev.append({"minute": (d + 1) * 1440, "kind": "sleep", "asleep": False})      # 06:00
    if work:
        for d in range(1, 4):
            for hh in (8, 9, 10, 11, 13, 14, 15, 16):
                m0 = d * 1440 + (hh - 6) * 60
                ev.append({"minute": m0, "kind": "activity", "rate": RATE[cls]})
                if per_hour < 60 or hh in (11, 16):
                    ev.append({"minute": m0 + per_hour, "kind": "activity", "rate": IDLE})
    ev.sort(key=lambda e: e["minute"])
    rows, _ = RL.replay_arm(ev, minutes=4 * 1440, backend="server", start_age=6.0,
                            player={"weight": w, "female": False}, rng="half")
    hs = [r["HUNGER"] for r in rows[1440:]]
    awake = [x for m, x in enumerate(hs) if not (20 <= (m // 60) % 24 < 24)]   # 02:00-06:00 is hours 20-24 from 06:00
    return sum(awake) / len(awake)


def karl_server(host, w, cls, rest_kcal, paee):
    """(minutes of work an hour, BAL %, DEF %) against REST, as karl() reads them."""
    per_hour = min(60, int(round(paee / 8 / ex_per_min(host, cls, w))))
    work = rest_kcal + paee
    rest = karl_arm(host, rest_kcal, rest_kcal, False, w, per_hour, cls)
    bal = karl_arm(host, 1.18 * work, rest_kcal, True, w, per_hour, cls)
    dfc = karl_arm(host, 0.57 * work, rest_kcal, True, w, per_hour, cls)
    return per_hour, round(100 * (bal / rest - 1), 1), round(100 * (dfc / rest - 1), 1)


KARL_E_KG = 119.1                 # the stand-in whose idle day (awake 20 h) is the oracle's 2,700 kcal
KARL_C_KG = 61.0                  # the stand-in whose 480 HeavyWork minutes bill the study's 9.6 MJ


def test_karl_2021_on_the_server_path_reads_with_its_twin(host):
    # S1325: -55 % (BAL) and +26 % (DEF), each within 1.5x (DEF 17.3 to 39 %); the oracle reads -57.0 and +19.3 (vigorous)
    # and -45.0 and +55.2 (not vigorous, a named non-reproduction). On the server the DEF reading is set by the twin:
    # E 65.7 (fails above), Env 75.8, V 23.2 (passes), C 10.2 (fails below)
    assert abs(idle_day(host, KARL_E_KG, 20) - A.KARL_REST) < 2.0
    assert abs(ex_per_min(host, "HeavyWork", KARL_C_KG) * 480 - A.KARL_PAEE) < 1.0
    e = karl_server(host, KARL_E_KG, "HeavyWork", A.KARL_REST, A.KARL_PAEE)
    env = karl_server(host, KARL_E_KG, "MediumWork", A.KARL_REST, A.KARL_PAEE)
    v = karl_server(host, 70.0, "HeavyWork", idle_day(host, 70.0, 20), A.KARL_PAEE)
    c = karl_server(host, KARL_C_KG, "HeavyWork", idle_day(host, KARL_C_KG, 20), ex_per_min(host, "HeavyWork", KARL_C_KG) * 480)
    assert (e, env, v, c) == ((31, -47.1, 65.7), (54, -43.4, 75.8), (52, -56.7, 23.2), (60, -60.4, 10.2)), (e, env, v, c)
    assert [A.karl_pass(x[1], x[2]) for x in (e, env, v, c)] == [(True, False), (True, False), (True, True), (True, False)]


# --- King 2011 at steady state (S1312) -----------------------------------------------------------------------------

KING_KG = 116.0                   # the stand-in whose idle day (awake 16 h) is the oracle's 2,500 kcal


def king_steady_server(host):
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
    # S1312 (the oracle's band: exercise within a quarter of the restriction's rise and under 3.3 mm of control)
    assert abs(idle_day(host, KING_KG, 16) - 2500.0) < 2.0
    bout, k = king_steady_server(host)
    rise = k["restriction"] - k["control"]
    band = abs(k["exercise"] - k["control"])
    assert bout == 73
    assert rise > 0.02 and band < 0.25 * rise and band * A.MM_PER_HUNGER < 3.3, k
    assert (round(rise, 4), round(band * A.MM_PER_HUNGER, 2)) == READ["king"], (rise, band * A.MM_PER_HUNGER)


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
    out = [be.K.energy.lagged(rows[i]["satiety.L"]) / k[i // spd] for i in range(from_day * spd, days * spd)]
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
    # day 1 0.0414; the server's lag is the same kernel stepped on the billed exercise kcal
    hi, lo = whybrow_server(host, 3.5), whybrow_server(host, 1.75)
    for bout, share, day1 in (hi, lo):
        assert max(share / 0.30, 0.30 / share) <= A.TOL and day1 < 0.05, (bout, share, day1)
    assert (hi[0], round(hi[1], 4), round(hi[2], 4)) == (53, 0.2985, 0.0414), hi
    assert (lo[0], round(lo[1], 4), round(lo[2], 4)) == (27, 0.2987, 0.0413), lo


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
    rise = host.call("hybrid.hungerTarget", 1 - M.H_REQ, e) - host.call("hybrid.hungerTarget", 1 - M.H_REQ, 1)
    return e, rise * M.MM_PER_HUNGER


def test_a_25_percent_deficit_on_the_server_path(host):
    # S1255 (< 10 mm over 2 y): the oracle's arithmetic reads 13.5 mm on a 2,500 kcal day (-625 kcal); the 70 kg man's
    # quarter deficit (-487 kcal) on the pipeline, a week in
    e, mm = deficit_server(host)
    assert (round(e, 4), round(mm, 1)) == READ["s1255"], (e, mm)


# the readings the tests above pin that their own lines do not spell out (each at the shipped constants)
READ = {
    "lowcarb_g": (1.0, 1.0, 0.967),     # g: the mixed arm at 08:00 and 20:00 of day 1, the low arm at 20:00 (oracle 0.951)
    "lowcarb_des": 0.0,                 # the low arm's es less the mixed arm's at 20:00 (the oracle's 0 too)
    "king": (0.1043, 2.43),             # the restriction's late rise (oracle 0.1552) and exercise's distance in mm (oracle 2.43)
    "s1255": (1.0492, 16.0),            # es over day 7 and its rise at the request, mm (the oracle's arithmetic 13.5 mm)
}
