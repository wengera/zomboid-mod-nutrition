"""NR.StimulantRealism (Plan 15 Task 10, spec section 5): Game (1, the default) or Realistic (2).

The option selects the kernel's active stimulant set K.acute.C once, at the server's options read
(K.acute.useStimulants). Realistic keeps the Plan 14 constants byte for byte (CAF_OFF_MAX 0.35, INTOX_FULL_BAC 0.20,
HANG_H 6 and the hangover row mNut 1.15, stress 0.10); Game overrides sizes only (0.12, 0.31, 3 and half each hangover
size). The timing is the same science in both: these tests pin each set's readings and show the kinetics (absorption,
clearance, the hangover's start) identical across the sets for the same intake.

The four-beer readings run the mod's server pipeline (tools/replay_live.ServerReplay, the guide's S6b scenario: four
0.3 L beers 20 minutes apart from 08:00, the stand-in's own first-sight body): the decision's "four beers peak at
about 31" (Realistic) is this schedule's reading, and Game's 0.31 % map puts it at about 20. One beer an hour clears
more between cans: both sets peak lower there (about 12 and 19) and neither reaches the 0.05 % hangover threshold.
"""
import math
import os
import sys
from contextlib import contextmanager

import pytest

from .server_host import REPO

sys.path.insert(0, os.path.join(REPO, "tools"))
import replay_live as RL  # noqa: E402

TOL = 1e-12
MIN = 1 / 60
CUP_MG = 107.0                           # the coffee of S0797, the cup every caffeine row is sized on
VANILLA_CUP = 0.025                      # vanilla's FATIGUE fall a cup (the guide's S6a-v-model)
GUIDE_BEERS = (60, 80, 100, 120)         # the guide's S6b: four 0.3 L beers from 08:00, one every 20 minutes
HOURLY_BEERS = (60, 120, 180, 240)       # one an hour


def _same(host, a, b):
    return host.rt.eval("function(a, b) return rawequal(a, b) end")(a, b)


@contextmanager
def _stim(host, mode):
    old = host.K.acute.C.MODE
    host.K.acute.useStimulants(mode)
    try:
        yield host.K.acute.C
    finally:
        host.K.acute.useStimulants(old)


# --- the two sets ----------------------------------------------------------------------------------------------

def test_realistic_keeps_the_plan_14_constants(host):
    A = host.K.acute
    assert host.py(A.STIM_REALISTIC) == {"MODE": 2, "CAF_OFF_MAX": 0.35, "INTOX_FULL_BAC": 0.20, "HANG_H": 6}
    assert host.K.effects.CAF_OFF_MAX is None and host.K.effects.INTOX_FULL_BAC is None   # one source: the sets
    assert A.HANG_H is None


def test_game_is_the_realistic_set_with_its_overrides(host):
    A = host.K.acute
    over = host.py(A.STIM_GAME_OVERRIDES)
    assert over == {"MODE": 1, "CAF_OFF_MAX": 0.12, "INTOX_FULL_BAC": 0.31, "HANG_H": 3}
    real = host.py(A.STIM_REALISTIC)
    assert set(over) <= set(real)                                       # an override names a realistic constant
    assert host.py(A.STIM[1]) == dict(real, **over)
    assert _same(host, A.STIM[2], A.STIM_REALISTIC)


def test_game_is_the_default_and_use_selects_once(host):
    A = host.K.acute
    assert A.C.MODE == 1 and _same(host, A.C, A.STIM[1])               # the session's set: Game
    try:
        assert _same(host, A.useStimulants(2), A.STIM[2]) and _same(host, A.C, A.STIM[2])
        assert _same(host, A.useStimulants(1), A.STIM[1]) and _same(host, A.C, A.STIM[1])
        A.useStimulants(2)
        assert _same(host, A.useStimulants(3), A.STIM[1])               # out of range: Game
        A.useStimulants(2)
        assert _same(host, A.useStimulants(None), A.STIM[1])
    finally:
        A.useStimulants(1)


# --- a cup's peak ----------------------------------------------------------------------------------------------

def _cup_peak_mg(host):
    """A 107 mg cup through the gut lane: the caffeine on board at its peak (82.942 mg at minute 111)."""
    A = host.K.acute
    a = A.new(0)
    a.gutCaf = CUP_MG
    peak = 0.0
    for _ in range(900):
        _, dose = A.absorbGut(a, MIN)
        A.caffeine(a, dose, 80, MIN)
        peak = max(peak, a.caf)
    return peak


def test_a_cups_fatigue_offset_in_each_set(host):
    f = host.K.effects.fOff
    with _stim(host, 2):                                                # Realistic: about -0.146 held
        real = f(0, CUP_MG, 0, 0)
        assert real == pytest.approx(-0.35 * 107 / 257, abs=TOL)        # -0.14572
        assert round(real, 3) == -0.146
    with _stim(host, 1):                                                # Game: about 2x vanilla's -0.025
        game = f(0, CUP_MG, 0, 0)
        assert game == pytest.approx(-0.12 * 107 / 257, abs=TOL)        # -0.04996
        assert -game / VANILLA_CUP == pytest.approx(2.0, abs=0.01)
    assert real / game == pytest.approx(0.35 / 0.12, abs=TOL)


def test_a_cups_peak_through_the_gut_lane(host):
    peak = _cup_peak_mg(host)
    assert peak == pytest.approx(82.94216766881858, abs=1e-9)          # the same in both sets: kinetics
    f = host.K.effects.fOff
    with _stim(host, 2):
        assert f(0, peak, 0, 0) == pytest.approx(-0.35 * peak / (peak + 150), abs=TOL)   # -0.12464
    with _stim(host, 1):
        assert f(0, peak, 0, 0) == pytest.approx(-0.12 * peak / (peak + 150), abs=TOL)   # -0.04273
    with _stim(host, 2):
        assert _cup_peak_mg(host) == peak


# --- the kinetics are the same in both sets -------------------------------------------------------------------------

def _evening(host, mode, beers_min, w=80.0, minutes=24 * 60, g=11.835):
    """The acute record's caffeine and alcohol minute by minute (a cup at minute 0, 0.3 L beers of 39.45 g/L
    ethanol at beers_min), under the given set; returns per-minute (caf, bac, hang, hangH, intox)."""
    A = host.K.acute
    out = []
    with _stim(host, mode):
        a = A.new(0)
        a.gutCaf = CUP_MG
        for m in range(minutes):
            if m in beers_min:
                a.gutAlc = a.gutAlc + g
            alc, caf = A.absorbGut(a, MIN)
            A.caffeine(a, caf, w, MIN)
            A.alcohol(a, alc, w, 1, MIN)
            out.append((a.caf, a.bac, a.hang, a.hangH, host.K.effects.intoxTarget(a.bac)))
    return out


def test_absorption_and_clearance_are_the_same_in_both_sets(host):
    game = _evening(host, 1, GUIDE_BEERS, w=65.0)
    real = _evening(host, 2, GUIDE_BEERS, w=65.0)
    assert [r[:2] for r in game] == [r[:2] for r in real]               # caffeine and blood alcohol, every minute
    sober = [next(m for m in range(130, len(x)) if x[m][1] == 0) for x in (game, real)]
    start = [next(m for m in range(len(x)) if x[m][2] == 1) for x in (game, real)]
    assert sober[0] == sober[1] and start == sober                      # the hangover starts at clearance in both


def test_the_hangover_lasts_its_sets_tail_after_clearance(host):
    for mode, tail in ((1, 3), (2, 6)):
        rows = _evening(host, mode, GUIDE_BEERS, w=65.0)
        peak = max(r[1] for r in rows)
        start = next(m for m in range(len(rows)) if rows[m][2] == 1)
        end = next(m for m in range(start, len(rows)) if rows[m][2] == 0)
        assert rows[start][3] == pytest.approx(tail * peak / 0.05, abs=1e-9)   # set at clearance, counted from the next minute
        assert (end - start) / 60 == pytest.approx(tail * peak / 0.05, abs=MIN + 1e-9)


# --- four beers on the server pipeline (the guide's S6b) ------------------------------------------------------------

def _replay(mode, beers_min):
    be = RL.ServerReplay(hour_offset=7.0, rng="half", sleep_allowed=False)
    be.rt.execute("SandboxVars = { NR = { StimulantRealism = %d } }" % mode)   # the options poll reads it each minute
    ev = [{"minute": m, "kind": "drink", "fluid": "Beer", "litres": 0.3} for m in beers_min]
    ev += [{"minute": m, "kind": "autodrop", "g": 500.0} for m in (30, 300, 600, 900)]
    ev.sort(key=lambda e: e["minute"])
    rows = RL.run(be, RL.synthetic_ages(1440), ev, ["acute.bac", "effects.intoxTarget", "acute.hang", "acute.hangH"],
                  start_age=0.0, dtms=[1.0] * 1440)
    assert be.K.acute.C.MODE == mode and be.NR.server.options.stimulantRealism == mode
    return rows


def _reading(rows, last_beer):
    pk = max(rows, key=lambda r: r.get("effects.intoxTarget") or 0)
    hang = [r for r in rows if r.get("acute.hang") == 1]
    sober = next(r["age"] for r in rows if r["age"] * 60 > last_beer and (r.get("acute.bac") or 0) == 0)
    return {"intox": pk["effects.intoxTarget"], "bac": pk["acute.bac"], "at": pk["age"], "sober": sober,
            "hang0": hang[0]["age"] if hang else None, "hangH": hang[0]["acute.hangH"] if hang else None,
            "hang1": hang[-1]["age"] if hang else None}


@pytest.fixture(scope="module")
def guide_beers():
    return {mode: _reading(_replay(mode, GUIDE_BEERS), GUIDE_BEERS[-1]) for mode in (1, 2)}


def test_four_beers_peak_at_about_31_realistic_and_20_game(guide_beers):
    g, r = guide_beers[1], guide_beers[2]
    assert r["intox"] == pytest.approx(31.27, abs=0.01)                 # the decision's Realistic reading
    assert g["intox"] == pytest.approx(20.17, abs=0.01)                 # Game: about 20
    assert g["intox"] / r["intox"] == pytest.approx(0.20 / 0.31, abs=TOL)
    assert g["bac"] == r["bac"] and g["at"] == r["at"]                  # the same blood alcohol, at the same minute


def test_four_beers_clear_and_hang_over_on_the_same_clock(guide_beers):
    g, r = guide_beers[1], guide_beers[2]
    assert g["sober"] == r["sober"] == g["hang0"] == r["hang0"]         # sober at 8.15 h, the hangover from then
    assert g["sober"] == pytest.approx(8.15, abs=MIN)
    assert r["hangH"] == pytest.approx(2 * g["hangH"], abs=1e-9)       # Realistic's 6 h tail against Game's 3 h
    assert r["hang1"] - r["hang0"] == pytest.approx(7.5, abs=0.02)      # 6 x 0.0625 / 0.05
    assert g["hang1"] - g["hang0"] == pytest.approx(3.75, abs=0.02)     # 3 x 0.0625 / 0.05


def test_one_beer_an_hour_peaks_lower_and_leaves_no_hangover():
    g = _reading(_replay(1, HOURLY_BEERS), HOURLY_BEERS[-1])
    r = _reading(_replay(2, HOURLY_BEERS), HOURLY_BEERS[-1])
    assert g["intox"] == pytest.approx(12.38, abs=0.01) and r["intox"] == pytest.approx(19.19, abs=0.01)
    assert g["bac"] == r["bac"] < 0.05 and g["hang0"] is None and r["hang0"] is None
    assert g["sober"] == r["sober"]
