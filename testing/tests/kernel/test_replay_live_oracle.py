"""tools/replay_live.py's own oracle (Plan 11f Task 2): fed the oracle tests' event lists, the replay reproduces their
pins exactly.

Where the oracle steps the satiety kernels (test_satiety_meal_studies.py's REPLAY: the stomach, the pool P and the
hunger function, one game minute a step), the replay runs the mod's own server adapters (ServerReplay) on the pipeline
steps that compose the same thing, kinetics then the writer, every other step left out so the energy state reads the
fresh body's 1 as the oracle holds it: the stomach drains in NR_Server_Kinetics, P decays and HUNGER is written by
NR_Server_Writer at the clock's circadian factor, held at 1 at 13:50 (NEUTRAL_HOUR) where the oracle holds it, and the
eats land through IN.land. The start record carries the oracle's P0 and the stamps (satiety.t, kineticsAge) so the first
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
adapters as a reading: the full pipeline on the oracle's 70 kg man (the stand-in's weight 70, male, responder 1) reads
day 2 at 1.348 and day 3 at 0.962 against the oracle's 1.304 and 0.986, the absorption over hours and the day
partition the difference. Plan 11f grades a live run against the server path; the oracle path names the distance.

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


def server_hunger(host, events, minutes, P0=None, h0=None):
    """The written HUNGER per minute (index i is minute i + 1), as M.hunger reads it."""
    if P0 is None:
        P0 = M.start_p(host, h0)
    a0 = 0.0 if h0 is None else h0
    start = {"username": "admin", "firstSeen": a0, "lastSeen": a0, "kineticsAge": a0,
             "satiety": {"P": P0, "S": 0, "L": 0, "t": a0}}
    rows, _ = RL.replay_arm(meal_events(events), start=start, minutes=minutes, start_age=a0, steps=SATIETY_STEPS,
                            hold_hour=RL.NEUTRAL_HOUR if h0 is None else None)
    assert [r["age"] for r in rows] == RL.synthetic_ages(minutes, a0)
    return [r["HUNGER"] for r in rows]


def test_the_neutral_hour_holds_the_circadian_factor_at_exactly_1(host):
    assert host.call("satiety.circadian", RL.NEUTRAL_HOUR) == 1.0


def test_the_650_kcal_meal_returns_to_the_request_at_minute_320(host):
    hs = server_hunger(host, {0: [("food", M.mixed(650))]}, 900)
    ref = M.hunger(host, {0: [("food", M.mixed(650))]}, 900)
    assert max(abs(a - b) for a, b in zip(hs, ref)) < 1e-12
    assert M.request(hs) == M.request(ref) == 320


def test_callahans_minutes_from_the_request_and_fasted_at_09_00(host):
    seeded = [M.request(server_hunger(host, {0: [("drink", M.preload(k))]}, 900, h0=M.CALLAHAN_H))
              for k in (190.0, 400.0, 825.0)]
    fasted = [M.request(server_hunger(host, {0: [("drink", M.preload(k))]}, 900, P0=0.0, h0=M.CALLAHAN_H),
                        fasted=True) for k in (190.0, 400.0, 825.0)]
    assert seeded == fasted == [250, 279, 339]


def test_marmoniers_snack_delays(host):
    base = M.request(server_hunger(host, {0: [("food", M.mixed(650))]}, 1500))
    d = {}
    for name, main, share in (("p", "proteins", 0.77), ("c", "carbs", 0.84), ("f", "lipids", 0.58)):
        hs = server_hunger(host, {0: [("food", M.mixed(650))], 240: [("food", M.snack(239.0, main, share))]}, 1500)
        d[name] = M.request(hs, after=245) - base
    assert (d["p"], d["c"], d["f"]) == (193, 159, 167)


def test_melansons_fasted_drinks(host):
    got = [M.request(server_hunger(host, {0: [("drink", M.snack(239.0, main, 0.70, water=400.0))]}, 900, P0=0.0),
                     fasted=True) for main in ("carbs", "lipids")]
    assert got == M.melanson(host) == [236, 236]


def test_the_fasted_400_kcal_breakfast_and_the_protein_contrast(host):
    v = M.mixed(400, water=250.0)
    assert M.held(server_hunger(host, {0: [("food", v)]}, 900, P0=0.0)) == M.held(
        M.hunger(host, {0: [("food", v)]}, 900, P0=0.0))
    hi = M.mixed(400.0, water=300.0, p=0.30, c=0.35, f=0.35)
    lo = M.mixed(400.0, water=300.0, p=0.10, c=0.55, f=0.35)
    hh = server_hunger(host, {0: [("food", hi)]}, 240)
    hl = server_hunger(host, {0: [("food", lo)]}, 240)
    d = sum(b - a for a, b in zip(hh, hl)) / 240
    assert abs(d - M.protein_contrast(host)) < 1e-12 and round(d, 4) == 0.0134


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
    extra = {"satiety": False} if backend == "oracle" else {}
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
    assert round(r2, 3) == 1.304 and round(r3, 3) == 0.986
    assert [round(ifed[W + 2]), round(ifed[W + 3])] == [1963, 1937] and round(ifast[W + 2]) == 2560
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
    assert [round(r, 4) for r in ratios] == [1.0075, 0.994, 0.9978]
    hours = [int((M.STEADY_DAYS - 1) * 1440 + h * 60) for h in range(1, 25)]
    es = [rows[m - 1]["body.energyState"] for m in hours]
    assert round(min(es), 4) == 1.0004 and round(max(es), 4) == 1.0005


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
        total = total + r["HUNGER"]
    return total


def test_six_meals_against_three_held_and_live(host):
    held = six_sum(6, 150, True) / six_sum(3, 300, True)
    live = six_sum(6, 150, False) / six_sum(3, 300, False)
    assert abs(held - M.meal_frequency_ratio(host)) < 1e-12 and round(held, 3) == 0.969
    assert live == M.meal_frequency_ratio_live(host) and round(live, 3) == 0.994


def test_the_36_h_fast_through_the_server_adapters_is_the_named_gap(host):
    fed, fast, days = fast_plans()
    kw = {"player": {"weight": 70.0, "female": False}, "rng": "half"}
    _, bf = energy_run(fed, days, backend="server", **kw)
    _, bx = energy_run(fast, days, backend="server", **kw)
    body = bf.record().body
    assert body.r == 1 and body.sex == 1 and abs(bf.maint() - 1948.73) < 0.01   # the oracle's 70 kg man
    W = M.FAST_WARM_DAYS
    ifed, ifast = RL.intake_by_day(bf.eats), RL.intake_by_day(bx.eats)
    r2, r3 = ifast[W + 2] / ifed[W + 2], ifast[W + 3] / ifed[W + 3]
    assert r2 > 1 and r3 < r2                                   # the oracle's direction (ruling 11d-3)
    assert (round(r2, 3), round(r3, 3)) == (1.348, 0.962), (r2, r3)


# --- the writer replays and monotony through the server adapters ----------------------------------------------------

def nicotine_written(host, ageH, w, anchorH):
    """M.nicotine_written's reading: a fresh record eaten at the request, the writer step alone."""
    c = host.call("satiety.circadian", (ageH + M.CLOCK_H) % 24)
    sat = {"P": host.call("satiety.seedP", M.H_REQ / c, 0, 1), "S": 0, "L": 0}
    if anchorH is not None:
        sat["nicH"] = anchorH + M.CLOCK_H
    rec = {"username": "admin", "firstSeen": 0.0, "lastSeen": 0.0, "satiety": sat}
    rows, _ = RL.replay_arm([], start=rec, ages=[ageH + M.CLOCK_H], steps=("writer",),
                            stats={"NICOTINE_WITHDRAWAL": w})
    return rows[0]["HUNGER"]


def test_the_nicotine_next_day_ratio(host):
    quit = [nicotine_written(host, 24 + m / 60, 0.51, 0.0) for m in M.MEAL_MINUTES]
    ctrl = [nicotine_written(host, 24 + m / 60, 0.0, None) for m in M.MEAL_MINUTES]
    assert all(abs(x - M.H_REQ) < 1e-9 for x in ctrl)
    r = sum(650.0 * x / M.H_REQ for x in quit) / sum(650.0 * x / M.H_REQ for x in ctrl)
    assert r == M.nicotine_ratio(M.writer_host(), 1)
    assert round(r, 4) == M.PIN_NEXT == 1.1304


def test_the_fifth_daily_eat_of_a_study_food_reads_a_stale_item(host):
    want = 4.3 * sum(2 ** (-k * 24 / 72.0) for k in range(1, 5))
    for food, scale, pin in (("TKX.Mono450", 1.0, 9.978), ("TKX.Staple450", 0.25, 2.4945)):
        a0 = 1000.0
        ev = [{"age": a0 + d * 24, "kind": "eat", "food": food} for d in range(5)]
        rows, be = RL.replay_arm(ev, ages=[a0 + d * 24 + 1 / 60 for d in range(5)], start_age=a0 - 1 / 60,
                                 paths=("lastIntake.source",))
        adds = [e["boredom"] for e in be.eats]
        assert adds[0] == 0 and [e["unhappy"] for e in be.eats] == adds
        assert adds[4] == pytest.approx(want * scale, rel=1e-12)
        assert round(adds[4], 4 if scale < 1 else 3) == pin
        assert rows[-1]["lastIntake.source"] == "declared"
