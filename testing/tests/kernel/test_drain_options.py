"""The drain options (Plan 17 Task 3, spec docs/superpowers/specs/2026-10-19-health-combine-design.md@program-record-v19 sections 2.4, 4.2
and 4.3): NR.DeathPace and NR.HealthCombine, read in the options poll, hoisted into K.drain.OPT with the day length
once a server minute (NR_Server_Effects' EFF.writeDrainOptions, called directly by the players' minute, P.minute), and the replay host's inputs for them.

- The option read: the sandbox's leaves reach K.drain.OPT within one server minute, an out-of-range leaf reads its
  default, a change is logged, and the day length is read once a server minute, never per player.
- The vanilla oracle (spec section 4.3): Vanilla pace with Add, on the replay host, a fresh default body with no food
  and the guide's S2d water, dies on tools/vanilla_model.py's fast death time.
- The properties (spec section 4.2) over the S2d fast with water and no vitamins at every pace: the target under Worst
  only >= under Multiply >= under Add at every minute, and under Worst and Multiply health reaches 0 only where some
  state's fraction is 0.
"""
import math
import os
import sys

import pytest

from . import golden_trace
from .server_host import REPO, Host

TOOLS = os.path.join(REPO, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
import mod_guide_series as G  # noqa: E402
import replay_live as RL  # noqa: E402
import vanilla_model as VM  # noqa: E402

FRACS = ["drain.frac.%d" % c for c in range(1, 8)]
MIN_H = 1.0 / 60.0


def _opt(h):
    O = h.K.drain.OPT
    return (O.pace, O.combine, O.dayMin)


# --- the option read ------------------------------------------------------------------------------------------------

def test_the_options_poll_sets_the_drain_options_after_one_server_minute():
    h = Host()
    assert _opt(h) == (3, 2, 90)                                          # the kernel's defaults: Realistic, Multiply
    h.rt.execute("SandboxVars = { NR = { DeathPace = 1, HealthCombine = 3 } }")
    h.online()
    opt = h.K.drain.OPT
    h.minute()
    assert _opt(h) == (1, 3, 90)                                          # no sandbox day length: vanilla's 90 minutes
    assert h.rt.eval("function(a, b) return rawequal(a, b) end")(opt, h.K.drain.OPT)   # written in place
    O = h.NR.server.options
    assert (O.deathPace, O.healthCombine) == (1, 3)
    assert "[NutritionRevamp] options: death pace 1, health combining 3" in h.printed()


def test_an_out_of_range_or_missing_leaf_reads_its_default_and_a_change_is_logged_once():
    h = Host()
    h.online()
    h.rt.execute("SandboxVars = { NR = { DeathPace = 4, HealthCombine = 0 } }")
    h.minute()
    assert _opt(h)[:2] == (3, 2)
    h.rt.execute("SandboxVars = { NR = { DeathPace = 2 } }")
    h.minute()
    h.minute()
    assert _opt(h)[:2] == (2, 2)
    said = [p for p in h.printed() if "options: death pace" in p]
    assert said == ["[NutritionRevamp] options: death pace 3, health combining 2",     # OnServerStarted
                    "[NutritionRevamp] options: death pace 2, health combining 2"]     # the change, once


def test_the_day_length_is_read_once_a_server_minute_and_seeds_every_players_minute():
    # Rule 6: the hoist reads getDayLengthMinutes once a server minute and NR_Server_Minute seeds it on every player's
    # context, so neither Effects' heal nor the writer reads it again; K.drain.OPT.dayMin follows a change next minute
    h = golden_trace.new_host()
    C = h.rt.eval("{ day = 0, len = 60 }")
    h.rt.eval("function(C) NutritionRevamp.sandbox().getDayLengthMinutes = function(s) C.day = C.day + 1; "
              "return C.len end end")(C)
    players = [golden_trace._new_player(h, n, golden_trace.MACROS[n]) for n in ("g1", "g2", "g6")]
    h.online(*players)
    start = golden_trace.START_AGE
    for m in range(1, 4):
        h.T.age = start + m / 60.0
        h.minute()
        h.tick(golden_trace.TICKS)
    assert h.K.drain.OPT.dayMin == 60
    b = h.record("g6")["body"]
    h.record("g6")["fluids"]["water"] = -0.12 * (b["fm"] + b["lm"] + b["lx"]) * 1000.0     # a drain heals and writes
    H = h.rt.eval("{ n = 0 }")
    h.rt.eval("function(H) local E = NutritionRevamp.server.effects; local f = E.writeDrainOptions; "
              "E.writeDrainOptions = function() H.n = H.n + 1; return f() end end")(H)
    day0 = C.day
    for m in range(4, 14):
        h.T.age = start + m / 60.0
        h.minute()
        h.tick(golden_trace.TICKS)
    assert h.record("g6")["drain"]["active"] is True
    assert C.day - day0 == 10                                             # one read a server minute, three players
    assert H.n == 10                                                      # the drain options' write: once a server minute
    C.len = 45
    h.T.age = start + 14 / 60.0
    h.minute()
    assert h.K.drain.OPT.dayMin == 45 and h.NR.read.minuteDayMin == 45


def test_an_unreadable_day_length_writes_vanillas_90_minutes():
    h = Host()
    h.online()
    h.K.drain.OPT.dayMin = 60
    h.minute()
    assert h.NR.read.minuteDayMin is None and h.K.drain.OPT.dayMin == 90


def test_the_replay_host_takes_the_drain_options_as_inputs():
    be = RL.ServerReplay(hour_offset=7.0, rng="half", sleep_allowed=False)
    assert be.drain_options == (RL.DEATH_PACE, RL.HEALTH_COMBINE, RL.DAY_MINUTES) == (3, 2, 90)
    RL.run(be, RL.synthetic_ages(1), [], [], start_age=0.0)
    assert _opt(be) == (3, 2, 90)
    be = RL.ServerReplay(hour_offset=7.0, rng="half", sleep_allowed=False, sex_specific=True, death_pace=2,
                         health_combine=1, day_minutes=60)
    RL.run(be, RL.synthetic_ages(1), [], [], start_age=0.0)
    assert _opt(be) == (2, 1, 60) and be.NR.server.options.sexSpecific is True
    be.set_drain_options(1, 3, 120)                                       # an admin's change: the next minute
    RL.run(be, RL.synthetic_ages(1, 1 / 60.0), [], [], start_age=1 / 60.0)
    assert _opt(be) == (1, 3, 120)
    with pytest.raises(ValueError):
        RL.ServerReplay(sleep_allowed=False, death_pace=None)
    with pytest.raises(ValueError):
        RL.ServerReplay(sleep_allowed=False, death_pace=4)


# --- the vanilla oracle (spec section 4.3) --------------------------------------------------------------------------

# The tolerance: the mod's Starving onset comes earlier than vanilla's level-4 hunger, 34.45 h after the last meal (the
# S2d series note's measured Starving hour, tools/mod_guide_series.py, re-read off this replay) against 34.84 h
# (tools/vanilla_model.py's level-4 hour on the same fast), so the death comes earlier by the onset difference; one
# game minute more allows for the replay's minute steps.
MOD_STARVING_H = 34.45
VANILLA_LEVEL4_H = 34.84
ORACLE_TOL_H = (VANILLA_LEVEL4_H - MOD_STARVING_H) + MIN_H
ORACLE_DT_MIN = 0.01        # the model's step: at its 1-minute step its death reads 62.917 h, 1.25 minutes past its own
                            # 62.896 h (the step places level 4 at 34.85 h, the first step past the 34.837 h crossing)


def _guide_run(days, pace, combine, paths):
    be = G._guide_replay()(hour_offset=G.HOUR_OFFSET, rng="half", sleep_allowed=False, death_pace=pace,
                           health_combine=combine)
    ev = G.sort_events([G.FRESH] + G.autodrops(days))
    return RL.run(be, RL.synthetic_ages(days * 1440), ev, paths, start_age=0.0), be


def _vanilla_fast_death():
    """tools/vanilla_model.py's fast (mod_guide_series._vanilla_fast's scenario: HUNGER from 0, no food, 0.25 L of water
    every 4 h, a fresh 80 kg character) at a step fine enough that its own grid moves its death by under a second:
    (level-4 hour, death hour)."""
    ev = [{"t_h": float(t), "kind": "drink", "fluid": "water", "litres": 0.25} for t in range(4, 72, 4)]
    sim = VM.simulate({"hours": 64.0, "dt_min": ORACLE_DT_MIN, "start": {"hunger": 0.0}, "events": ev})
    level4 = next(t for t, x in sim["hunger"] if VM.moodle_level(x, VM.HUNGRY_THRESHOLDS) >= 4)
    return level4, next(t for t, x in sim["health"] if x <= 0)


def test_vanilla_pace_with_add_dies_on_vanillas_fast_death_time():
    level4, vanilla_death = _vanilla_fast_death()
    assert round(level4, 2) == VANILLA_LEVEL4_H and round(vanilla_death, 1) == 62.9
    rows, be = _guide_run(3, 1, 3, ["drain.starving", "drain.state"])
    assert _opt(be) == (1, 3, 90)
    starving = next(r["age"] for r in rows if r.get("drain.starving"))
    assert round(starving, 2) == MOD_STARVING_H
    death = next(r["age"] for r in rows if r[G.HEALTH] <= G.DEATH_HEALTH)
    assert all(r.get("drain.state") in (None, 0, 1) for r in rows)        # starvation alone: the water holds
    assert abs(death - vanilla_death) <= ORACLE_TOL_H, (death, vanilla_death)
    # the line from the onset: vanilla's own level-4 drain, 100 / 3.564 h at the 90-minute day
    assert death - starving == pytest.approx(100 / (be.K.drain.R_HUNGER * 90), abs=MIN_H)


# --- the properties (spec section 4.2) ------------------------------------------------------------------------------

# The guide's S2d fast (no food, the replay's water, no vitamins) under Worst only at each pace, until two days past the
# death: Vanilla and Shortened kill by starvation alone, Realistic by wet beriberi on day 77.23 with starvation, scurvy
# and pellagra active. A fraction that reaches 0 stays there (the curve and the line clamp at their death point), so
# from the death on every rule's target is 0 and the rest of the 90 days adds nothing.
PROPERTY_DAYS = {1: 4, 2: 18, 3: 80}
PROPERTY_DEATH_H = {1: 62.50, 2: 370.43, 3: 1853.45}      # Worst only's death, read off each replay
FTOL = 1e-12


def _fold(fracs, rule):
    if rule == "worst":
        return 100.0 * min(fracs)
    if rule == "multiply":
        return 100.0 * math.prod(fracs)
    return 100.0 * max(0.0, 1.0 - sum(1.0 - f for f in fracs))


def _health(rows, targets):
    """Health under a target series, from 100, by the adapter's take (K.drain.take): each minute falls toward the
    target by at most the minute's drain (drain.drainThisMinute, the sum of the active rates: the same under every
    rule), never past it. The fast's targets never rise, so no heal enters."""
    hp, out = 100.0, []
    for r, t in zip(rows, targets):
        if t is not None:
            hp -= min(max(hp - t, 0.0), r["drain.drainThisMinute"])
        out.append(hp)
    return out


@pytest.fixture(scope="module", params=sorted(PROPERTY_DAYS))
def fast(request):
    pace = request.param
    rows, be = _guide_run(PROPERTY_DAYS[pace], pace, 1, FRACS + ["drain.target", "drain.drainThisMinute"])
    assert _opt(be) == (pace, 1, 90)
    return pace, rows


def test_the_targets_order_worst_multiply_add_at_every_minute(fast):
    pace, rows = fast
    seen = 0
    for r in rows:
        fr = [r[p] for p in FRACS if r.get(p) is not None]
        if not fr:
            assert r.get("drain.target") in (None, 100)                     # no state (none before the record)
            continue
        seen += 1
        w, m, a = _fold(fr, "worst"), _fold(fr, "multiply"), _fold(fr, "add")
        assert r["drain.target"] == pytest.approx(w, abs=1e-9)                 # the live Worst target is the fold
        assert w >= m - FTOL and m >= a - FTOL, (r["age"], fr)
    assert seen > 0
    many = [r for r in rows if sum(r.get(p) is not None for p in FRACS) >= 2]
    assert bool(many) is (pace == 3)                                          # Realistic reaches the vitamin states
    assert any(_fold([r[p] for p in FRACS if r.get(p) is not None], "add") <
               _fold([r[p] for p in FRACS if r.get(p) is not None], "multiply") - 1 for r in many) is (pace == 3)


def test_health_reaches_0_only_where_some_fraction_is_0_under_worst_and_multiply(fast):
    pace, rows = fast
    fr = [[r[p] for p in FRACS if r.get(p) is not None] for r in rows]
    worst_live = [r[G.HEALTH] for r in rows]
    worst = _health(rows, [_fold(f, "worst") if f else None for f in fr])
    assert max(abs(x - y) for x, y in zip(worst, worst_live)) < 1e-9          # the take rule reproduces the live health
    multiply = _health(rows, [_fold(f, "multiply") if f else None for f in fr])
    for name, hp in (("worst", worst_live), ("multiply", multiply)):
        dead = [k for k, x in enumerate(hp) if x <= G.DEATH_HEALTH]
        assert dead, name
        for k in dead:
            assert min(fr[k]) <= G.DEATH_HEALTH / 100.0, (name, rows[k]["age"], fr[k])
    first = next(k for k, x in enumerate(worst_live) if x <= G.DEATH_HEALTH)
    assert rows[first]["age"] == pytest.approx(PROPERTY_DEATH_H[pace], abs=MIN_H)
    assert rows[-1]["age"] - rows[first]["age"] >= 24.0                       # the replay runs past the death


# --- Plan 17 close M1: the stand-in's HUNGRY and THIRST levels --------------------------------------------------------

@pytest.mark.parametrize("stat,moodle,cases", [
    ("HUNGER", "HUNGRY", [(0.10, 0), (0.16, 1), (0.26, 2), (0.46, 3), (0.70, 3), (0.71, 4), (1.0, 4)]),
    ("THIRST", "THIRST", [(0.10, 0), (0.13, 1), (0.26, 2), (0.71, 3), (0.84, 3), (0.85, 4), (1.0, 4)]),
])
def test_the_stand_in_answers_hungry_and_thirst_from_its_stats_at_vanillas_thresholds(stat, moodle, cases):
    # close-review M1: the stand-in answered 0 for both, so a replay healed at tier 0 where the game adds nothing at
    # level 4 (#2721); vanilla's thresholds are #0508 and #0509, read back at these probes there
    h = golden_trace.new_host()
    p = golden_trace._new_player(h, "g1", golden_trace.MACROS["g1"])
    MT = h.rt.globals().MoodleType
    moodles = p.getMoodles(p)
    for v, level in cases:
        p.sv[stat] = v
        assert moodles.getMoodleLevel(moodles, MT[moodle]) == level, (stat, v)


def test_the_stand_ins_level_4_zeroes_the_awake_heal_addition():
    # the mod's own tier read off the stand-in's levels: Starving or Parched shows, so the addition is vanilla's 0
    h = golden_trace.new_host()
    p = golden_trace._new_player(h, "g1", golden_trace.MACROS["g1"])
    MT = h.rt.globals().MoodleType
    moodles = p.getMoodles(p)
    p.sv["HUNGER"], p.sv["THIRST"] = 0.75, 0.0
    hl = moodles.getMoodleLevel(moodles, MT.HUNGRY)
    tl = moodles.getMoodleLevel(moodles, MT.THIRST)
    assert (hl, tl) == (4, 0)
    assert h.K.drain.regenAddition(hl, tl, 0, False) == 0
    p.sv["HUNGER"] = 0.0
    assert h.K.drain.regenAddition(moodles.getMoodleLevel(moodles, MT.HUNGRY), tl, 0, False) == 0.002
