"""tools/replay_live.py's own oracle (Plan 11f Task 2): fed the oracle tests' event lists, the replay reproduces their
pins exactly.

Where the oracle steps the satiety kernels (test_satiety_meal_studies.py's REPLAY: the stomach, the meal pool M and
the hunger function, one game minute a step), the replay runs the mod's own server adapters (ServerReplay) on the
pipeline steps that compose the same thing, kinetics then the writer, every other step left out so the energy state
reads the fresh body's 1 as the oracle holds it: the intake feeds M at the eat, the stomach drains and M clears in NR_Server_Kinetics, and HUNGER is written by
NR_Server_Writer at the clock's circadian factor, held at 1 at 13:50 (NEUTRAL_HOUR) where the oracle holds it, and the
eats land through IN.land. The start record carries the oracle's M0 and the stamps (satiety.t, kineticsAge) so the first
minute steps as the oracle's does. Each reading equals the oracle function's own (and its pin).

The writer replays (the nicotine replay, test_satiety_meal_studies.py's nicotine_written) run the writer step alone on a
fresh record per meal, as the oracle does (a fresh hoist each meal). Monotony's anchor (test_kernel_monotony.py, 9.978,
and the staple's x 0.25) is read off five daily eats of TKX_StudyFoods' Mono450 and Staple450 through the intake
adapter's declared chain and IN.atEat, the BOREDOM and UNHAPPINESS adds the stand-in's Stats.add received.

The gap, named: the energy oracles (ENERGY_REPLAY, SIX_LIVE_REPLAY) step the kernels directly, with simplifications the
server path does not share (an eat's vector booked into the day at once with no stomach; no day partition, adaptive
thermogenesis or training close, so fatDep stays 0). The replay reproduces them exactly through its oracle backend
(OracleReplay, the same composition driven by the same event lists: sleep at 23:00 and waking at 07:00, the meals,
the request-level meal's kcal from the state the last minute left), and runs the same 36 h fast through the server
adapters as a reading: the full pipeline on the oracle's 70 kg man (the stand-in's weight 70, male, responder 1, idle
at the engine's Default class 1.5, billed standing quietly) reads day 2 at 1.196 and day 3 at 0.969 against the
simplified path's 1.186 and 0.976 since the deficit drive's refit on the server path (Plan 11f Task 2c fix 1; 1.174 and
0.974 against 1.166 and 0.979 in Task 2c, 1.342 and 0.974 against 1.304 and 0.986 before), the absorption over hours and the day partition the difference (re-pinned in Task 2
fix round 1: the stand-in idled at 1.3 before, which the mod bills as DrivingCar, and read 1.348 and 0.962).
Plan 11f grades a live run against the server path; the oracle path names the distance. Since Task 2c the energy
oracles themselves run the server path (test_replay_live_energy.py); the simplified composition is kept as this
backend's reference only.

The "312 min" the plan lists is pinned by no oracle test; the 650 kcal meal's request minute (320, which
test_a_650_kcal_mixed_meal_holds_hunger_off_for_four_to_five_hours bands at 240-330) and Callahan's pinned minutes
stand for it here.
"""
import os
import sys

import pytest

from . import test_satiety_meal_studies as M
from .server_host import REPO

sys.path.insert(0, os.path.join(REPO, "tools"))
import replay_live as RL  # noqa: E402

SATIETY_STEPS = ("kinetics", "writer")


# --- the satiety replays through the server adapters -------------------------------------------------------------

def meal_events(events):
    """The oracle's {minute: [(kind, vec), ...]} as replay events."""
    out = []
    for m in sorted(events):
        for kind, vec in events[m]:
            out.append({"minute": m, "kind": "drink" if kind == "drink" else "eat", "vec": vec})
    return out


def server_hunger(host, events, minutes, M0=None, h0=None):
    """The model's own hunger per minute (index i is minute i + 1; RL.H_MODEL, the pre-curve value since Plan 15 Task
    6), as M.hunger reads it."""
    if M0 is None:
        M0 = M.start_m(host, h0)
    a0 = 0.0 if h0 is None else h0
    start = {"username": "admin", "firstSeen": a0, "lastSeen": a0, "kineticsAge": a0,
             "satiety": {"M": M0, "S": 0, "L": 0, "t": a0}}
    rows, _ = RL.replay_arm(meal_events(events), start=start, minutes=minutes, start_age=a0, steps=SATIETY_STEPS,
                            hold_hour=RL.NEUTRAL_HOUR if h0 is None else None, constants=RL.WORLD_CLOCK)   # the body clock on the world hour (Plan 16 Task 4)
    assert [r["age"] for r in rows] == RL.synthetic_ages(minutes, a0)
    return [r[RL.H_MODEL] for r in rows]


def test_the_neutral_hour_holds_the_circadian_factor_at_exactly_1(host):
    assert host.call("satiety.circadian", RL.NEUTRAL_HOUR) == 1.0


def test_the_650_kcal_meal_returns_to_the_request_at_the_oracles_minute(host):
    # 310 under the refit (Plan 11g Task 6c fix 1; 302 under Task 6c's fit, 349 under the gut stage's fit, Task 6, 512 under G's provisional
    # constants, 320 on the P model), the oracle's reading, inside the 240-300 anchor's 1.1x
    hs = server_hunger(host, {0: [("food", M.mixed(650))]}, 900)
    ref = M.hunger(host, {0: [("food", M.mixed(650))]}, 900)
    assert max(abs(a - b) for a, b in zip(hs, ref)) < 1e-12
    assert M.request(hs) == M.request(ref) == 310


def test_callahans_minutes_from_the_request_and_fasted_at_09_00(host):
    seeded = [M.request(server_hunger(host, {0: [("drink", M.preload(k))]}, 900, h0=M.CALLAHAN_H))
              for k in (190.0, 400.0, 825.0)]
    fasted = [M.request(server_hunger(host, {0: [("drink", M.preload(k))]}, 900, M0=0.0, h0=M.CALLAHAN_H),
                        fasted=True) for k in (190.0, 400.0, 825.0)]
    assert seeded == fasted == [243, 266, 329]                  # Plan 11g Task 6c fix 1's refit (Task 6c: 234, 261, 321; G: 234, 273, 360; P: 250, 279, 339)


def test_marmoniers_snack_delays(host):
    base = M.request(server_hunger(host, {0: [("food", M.mixed(650))]}, 1500))
    d = {}
    for name, main, share in (("p", "proteins", 0.77), ("c", "carbs", 0.84), ("f", "lipids", 0.58)):
        hs = server_hunger(host, {0: [("food", M.mixed(650))], 240: [("food", M.snack(239.0, main, share))]}, 1500)
        d[name] = M.request(hs, after=245) - base
    assert (d["p"], d["c"], d["f"]) == (183, 156, 160)         # Plan 11g Task 6c fix 1's refit (Task 6c: 189, 160, 165; G: 149, 132, 126; P: 193, 159, 167)


def test_melansons_fasted_drinks(host):
    got = [M.request(server_hunger(host, {0: [("drink", M.snack(239.0, main, 0.70, water=400.0))]}, 900, M0=0.0),
                     fasted=True) for main in ("carbs", "lipids")]
    assert got == M.melanson(host) == [219, 217]               # Plan 11g Task 6c fix 1's refit (Task 6c: 217, 215; G: 156, 141; P: 236, 236)


def test_the_fasted_400_kcal_breakfast_and_the_protein_contrast(host):
    v = M.mixed(400, water=250.0)
    assert M.held(server_hunger(host, {0: [("food", v)]}, 900, M0=0.0)) == M.held(
        M.hunger(host, {0: [("food", v)]}, 900, M0=0.0))
    hi = M.mixed(400.0, water=300.0, p=0.30, c=0.35, f=0.35)
    lo = M.mixed(400.0, water=300.0, p=0.10, c=0.55, f=0.35)
    hh = server_hunger(host, {0: [("food", hi)]}, 240)
    hl = server_hunger(host, {0: [("food", lo)]}, 240)
    d = sum(b - a for a, b in zip(hh, hl)) / 240
    assert abs(d - M.protein_contrast(host)) < 1e-12 and round(d, 5) == 0.01256   # Plan 11g Task 6c fix 2's refit (fix 1: 0.01267; Task 6c: 0.01245; G: 0.0196; P: 0.0134)


def test_rolls_1999_and_the_minute_1_fullness(host):
    arms = {"soup": [("food", M.SOUP)], "cw": [("food", M.CASSEROLE), ("drink", M.WATER)],
            "cas": [("food", M.CASSEROLE)]}
    got = {n: M.KJ_PER_HUNGER * server_hunger(host, {0: ev}, 17)[16] for n, ev in arms.items()}
    ref = M.rolls_1999(host)
    assert all(abs(got[n] - ref[n]) < 1e-9 for n in arms), (got, ref)
    vols = [100.0, 200.0, 300.0, 400.0, 500.0, 600.0]
    got1 = [server_hunger(host, {0: [("food", {"water": g})]}, 1)[0] for g in vols]
    ref1 = [M.hunger(host, {0: [("food", {"water": g})]}, 1)[0] for g in vols]
    assert max(abs(a - b) for a, b in zip(got1, ref1)) < 1e-12


# --- the energy replays through the oracle backend ----------------------------------------------------------------

def sleep_events(days):
    """Asleep from 23:00 to 07:00 (ENERGY_REPLAY's hod >= 23 or hod < 7 at each minute's start)."""
    ev = [{"minute": 0, "kind": "sleep", "asleep": True}]
    for d in range(days):
        ev.append({"minute": d * 1440 + 7 * 60, "kind": "sleep", "asleep": False})
        ev.append({"minute": d * 1440 + 23 * 60, "kind": "sleep", "asleep": True})
    return ev


def energy_run(plan, days, backend="oracle", **kw):
    ev = sleep_events(days) + [{"minute": m, "kind": "meal", "size": k} for m, k in sorted(plan.items())]
    ev.sort(key=lambda e: e["minute"])
    extra = {"satiety": False} if backend == "oracle" else {"constants": RL.WORLD_CLOCK}   # the server path on the world hour (Plan 16 Task 4)
    extra.update(kw)
    return RL.replay_arm(ev, minutes=days * 1440, backend=backend, paths=("body.energyState", "body.eb24"), **extra)


def fast_plans():
    fed, fast = M.warm(), M.warm()
    for d, kind in ((0, "maint"), (1, "maint"), (2, "request"), (3, "request")):
        fed.update(M.meals_of(d, kind))
        if d != 1:
            fast.update(M.meals_of(d, kind))
    return fed, fast, M.FAST_WARM_DAYS + 4


def test_the_36_h_fast_ratios_and_log(host):
    fed, fast, days = fast_plans()
    _, bf = energy_run(fed, days)
    rx, bx = energy_run(fast, days)
    W = M.FAST_WARM_DAYS
    ifed, ifast = RL.intake_by_day(bf.eats), RL.intake_by_day(bx.eats)
    r2, r3 = ifast[W + 2] / ifed[W + 2], ifast[W + 3] / ifed[W + 3]
    o2, o3, olog, _, _ = M.fast_reading(host)
    assert r2 == o2 and r3 == o3
    assert round(r2, 3) == 1.141 and round(r3, 3) == 0.985              # Plan 11g Task 7 (1.186, 0.976 in Plan 11f Task 2c fix 1; 1.166, 0.979 in its Task 2c; 1.304, 0.986 before)
    assert [round(ifed[W + 2]), round(ifed[W + 3])] == [1948, 1939] and round(ifast[W + 2]) == 2223
    at = [M.at_hour(0, 20 + 12), M.at_hour(0, 20 + 24), M.at_hour(0, 20 + 36)]
    assert [rx[m - 1]["body.energyState"] for m in at] == [x["es"] for x in olog]
    assert [round(rx[m - 1]["body.eb24"]) for m in at] == [-1, -1301, -1950]


def test_the_steady_eater(host):
    plan = {}
    for d in range(M.STEADY_DAYS):
        plan.update({int(d * 1440 + h * 60): ("maint" if d == 0 else "request") for h in M.FAST_MEAL_H})
    rows, be = energy_run(plan, M.STEADY_DAYS)
    by = RL.intake_by_day(be.eats)
    ratios = [by[d] / be.maint() for d in (1, 2, 3)]
    assert ratios == M.steady_reading(host)[0]
    assert [round(r, 4) for r in ratios] == [0.9998, 0.995, 0.9958]      # Plan 11g Task 7 (1.0017, 0.9947, 0.9963 in Plan 11f Task 2c fix 1)
    hours = [int((M.STEADY_DAYS - 1) * 1440 + h * 60) for h in range(1, 25)]
    es = [rows[m - 1]["body.energyState"] for m in hours]
    assert round(min(es), 4) == 1.0012 and round(max(es), 4) == 1.0012   # Plan 11g Task 7 (1.0013 to 1.0015 before)


def six_sum(n, gap, hold):
    start = M.SIX_WARM_DAYS * 1440 + 480
    ev = sleep_events(M.SIX_WARM_DAYS + 2)
    wk = 2000.0 / 3
    for d in range(M.SIX_WARM_DAYS):
        for i in range(3):
            ev.append({"minute": d * 1440 + 480 + i * 300, "kind": "eat", "sate": False,
                       "vec": M.mixed(wk, water=300.0, fibre=6.0 * wk / 650)})
    k = 2000.0 / n
    for i in range(n):
        ev.append({"minute": start + i * gap, "kind": "eat", "vec": M.mixed(k, water=900.0 / n, fibre=6.0 * k / 650)})
    ev.sort(key=lambda e: e["minute"])
    rows, _ = RL.replay_arm(ev, minutes=(M.SIX_WARM_DAYS + 2) * 1440, backend="oracle", hold_es=hold)
    total = 0.0
    for r in rows[start:start + 1440]:            # in order, as the oracle's Lua sums (Python's sum() compensates)
        total = total + r[RL.H_MODEL]
    return total


def test_six_meals_against_three_held_and_live(host):
    held = six_sum(6, 150, True) / six_sum(3, 300, True)
    live = six_sum(6, 150, False) / six_sum(3, 300, False)
    assert abs(held - M.meal_frequency_ratio(host)) < 1e-12 and round(held, 3) == 0.974   # Plan 11g Task 6c fix 1's refit (Task 6c 0.951; the gut stage's fit 1.020; P: 0.969)
    assert live == M.meal_frequency_ratio_live(host) and round(live, 3) == 0.984     # Plan 11g Task 7's deficit refit (0.988 under Task 6c fix 1's satiety refit; Task 6c 0.964; the gut stage's fit 1.035; P: 0.983, Plan 11f Task 2c fix 1)


def test_the_36_h_fast_through_the_server_adapters_is_the_named_gap(host):
    fed, fast, days = fast_plans()
    kw = {"player": {"weight": 70.0, "female": False}, "rng": "half"}
    _, bf = energy_run(fed, days, backend="server", **kw)
    _, bx = energy_run(fast, days, backend="server", **kw)
    body = bf.record().body
    assert body.sex == 1 and abs(bf.maint() - 1948.73) < 0.01   # the oracle's 70 kg man (participant.py)
    W = M.FAST_WARM_DAYS
    ifed, ifast = RL.intake_by_day(bf.eats), RL.intake_by_day(bx.eats)
    r2, r3 = ifast[W + 2] / ifed[W + 2], ifast[W + 3] / ifed[W + 3]
    assert r2 > 1 and r3 < r2                                   # the oracle's direction (ruling 11d-3)
    assert (round(r2, 3), round(r3, 3)) == (1.145, 0.98), (r2, r3)      # a reading (Plan 16 Task 5's deficit arm on Forbes: 0.979 before; Plan 13 Task 10c's low-fat ramp; 1.148, 0.981 under Plan 11g Task 7; 1.196, 0.969 in Plan 11f Task 2c fix 1; 1.174 in its Task 2c, 1.342 before)


# --- the writer replays and monotony through the server adapters ----------------------------------------------------

def nicotine_written(host, ageH, w, anchorH):
    """M.nicotine_written's reading: a fresh record eaten at the request, the writer step alone."""
    c = host.call("satiety.circadian", (ageH + M.CLOCK_H) % 24)
    sat = {"M": host.call("satiety.seedMeal", M.H_REQ / c, 0, 1), "S": 0, "L": 0}
    if anchorH is not None:
        sat["nicH"] = anchorH + M.CLOCK_H
    rec = {"username": "admin", "firstSeen": 0.0, "lastSeen": 0.0, "satiety": sat}
    rows, _ = RL.replay_arm([], start=rec, ages=[ageH + M.CLOCK_H], steps=("writer",),
                            stats={"NICOTINE_WITHDRAWAL": w}, constants=RL.WORLD_CLOCK)   # the body clock on the world hour (Plan 16 Task 4)
    return rows[0][RL.H_MODEL]


def test_the_nicotine_next_day_ratio(host):
    quit = [nicotine_written(host, 24 + m / 60, 0.51, 0.0) for m in M.MEAL_MINUTES]
    ctrl = [nicotine_written(host, 24 + m / 60, 0.0, None) for m in M.MEAL_MINUTES]
    assert all(abs(x - M.request_written(host, 24 + m / 60)) < 1e-9 for x, m in zip(ctrl, M.MEAL_MINUTES))
    r = sum(650.0 * x / M.H_REQ for x in quit) / sum(650.0 * x / M.H_REQ for x in ctrl)
    assert r == M.nicotine_ratio(M.writer_host(), 1)
    assert round(r, 4) == M.PIN_NEXT == 1.1304


def test_the_fifth_daily_eat_of_a_study_food_holds_a_stale_item(host):
    want = 4.3 * sum(2 ** (-k * 24 / 72.0) for k in range(1, 5))
    for food, scale, pin in (("TKX.Mono450", 1.0, 9.978), ("TKX.Staple450", 0.25, 2.4945)):
        a0 = 1000.0
        ev = [{"age": a0 + d * 24, "kind": "eat", "food": food} for d in range(5)]
        rows, be = RL.replay_arm(ev, ages=[a0 + d * 24 + 1 / 60 for d in range(5)], start_age=a0 - 1 / 60,
                                 paths=("lastIntake.source",))
        assert all(e["boredom"] == 0 and e["unhappy"] == 0 for e in be.eats)     # no add at the eat (Plan 11f Task 9b)
        lvl = be.K.monotony.target(be.record().monotony, a0 + 4 * 24)[0]          # the floor's target after the fifth
        assert lvl == pytest.approx(want * scale, rel=1e-12)
        assert round(lvl, 4 if scale < 1 else 3) == pin
        assert rows[-1]["lastIntake.source"] == "declared"


# --- the stand-in's step (Plan 11g Task 6, carried from the Task 4 fix 1 review) ----------------------------------

def oracle_m(steps, trait=None):
    """OracleReplay's M and HUNGER after a 600 kcal meal at M 40, stepped by `steps` (game minutes each)."""
    be = RL.OracleReplay(M0=40.0, energy=False, satiety=True, hold_es=True, hold_hour=True)
    if trait is not None:
        be.ev_trait({"trait": trait}, 0.0)
    be.ev_eat({"vec": M.mixed(600)}, 0.0)
    age = 0.0
    for d in steps:
        age += d / 60
        be.step(age, float(d))
    return be.o.M, be.o.hunger


def test_a_three_minute_step_equals_three_one_minute_steps():
    # the stand-in drains the stomach and clears M in Kinetics' one-minute substeps (K.satiety.drain), so a ring step
    # of 3 minutes reads what three 1-minute steps read, as on the server
    m3, h3 = oracle_m([3] * 20)
    m1, h1 = oracle_m([1] * 60)
    assert m3 == pytest.approx(m1, rel=1e-9) and h3 == pytest.approx(h1, rel=1e-9)
    m60, _ = oracle_m([60])
    assert m60 == pytest.approx(m1, rel=1e-9)


def test_a_ninety_minute_step_equals_a_sixty_minute_capped_step():
    # the Task 6 review's finding 6: the study stand-in caps a step's drain at K.resume.STEP_M (60 game minutes; Plan 16
    # Task 2, K.satiety.MAX_GAP_M until then), so a 90-minute step drains and clears what a 60-minute step does, and a
    # step past the cap reads the same however far past it is
    m90, h90 = oracle_m([90])
    m60, h60 = oracle_m([60])
    assert m90 == m60 and h90 == h60
    assert oracle_m([300]) == (m60, h60)
    m61, _ = oracle_m([30, 31])                                    # under the cap each step clears its own length
    assert m61 < m60


def test_the_stand_in_clears_m_at_the_appetite_traits_factor():
    # the record's trait factor (K.satiety.trait, KIN.mealTrait's; the stand-in's sandbox multiplier is 1): a hearty
    # appetite clears faster, a light eater slower, each the same over a 3-minute step as over three 1-minute steps
    m, _ = oracle_m([1] * 60)
    ha3, _ = oracle_m([3] * 20, "HEARTY_APPETITE")
    ha1, _ = oracle_m([1] * 60, "HEARTY_APPETITE")
    le, _ = oracle_m([1] * 60, "LIGHT_EATER")
    assert ha3 == pytest.approx(ha1, rel=1e-9)
    assert ha1 < m < le


def test_the_stand_in_reads_the_kernels_step_bound():
    # Plan 11g close; Plan 16 Task 2: the study stand-in caps a step at the kernel's K.resume.STEP_M, the pipeline's
    # sub-step bound, with no copy (K.satiety.MAX_GAP_M is gone)
    assert "NR_O.MAX_GAP_M" not in RL.ORACLE_LUA and "MAX_GAP_M" not in RL.ORACLE_LUA
    assert "K.satiety.drain(o.st, K.min(dtM, K.resume.STEP_M), o)" in RL.ORACLE_LUA
