"""The replay's fidelity to the live game (Plan 16 Task 7; spec sections 4.3 and 5.1; carries sections 1, 3 and 4).

- Drinks sip by sip: vanilla drinks over its action's length in server wall time (20 ms a unit, #3766; water 460
  units) and the mod lands each sip as it is drunk, so a whole drink reaches the liquid lane over its span, which the
  day length turns into game minutes (tools/replay_live.py spread_drinks).
- The cold multiplier: the ring's `cold` field (or a `body.coldMult` path) feeds the stand-in thermoregulator's
  getEnergyMultiplier one row ahead (ring_cold_events), so the cold diuresis the live body booked replays (#3947).
- The overlays: "replay.LIQUID_SOLID_KCAL" (the liquid lane before Plan 15 Task 14b) and "replay.FAT_CEILING" (the
  deficit arm before Plan 16 Task 5) restore the rules of the last builds that held them (bcf99149 and 3a93d51c) on a
  replay host, exactly; x332's and x263's tests run at HEAD through them (test_replay_live_autodrop.py,
  test_replay_live_sleep.py)."""
import glob
import json
import os
import subprocess
import sys

import lupa.lua51 as lua51
import pytest

from .conftest import SHARED, kernel_files, pre_kernel_files
from .server_host import REPO

sys.path.insert(0, os.path.join(REPO, "tools"))
import replay_live as RL  # noqa: E402

ART = os.path.join(REPO, "testing", "artifacts")
X263 = os.path.join(ART, "x263-20261010-122318")
X452B = os.path.join(ART, "x452b-20261017-153935")
X456 = os.path.join(ART, "x456-20261017-074015")
X457 = os.path.join(ART, "x457-20261017-074403")
LIQ = "stomach.liquid"
WATER = "fluids.water"


# --- a bare kernel host (no coverage hook), a kernel file optionally taken from another build ------------------------

def git_show(commit, rel):
    try:
        return subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (commit, rel)], capture_output=True, check=True,
                              encoding="utf-8").stdout
    except (OSError, subprocess.CalledProcessError) as e:
        pytest.skip("no git history for %s at %s: %s" % (rel, commit, e))


def kernel_rt(replace=None):
    """NR_Core.lua and every NR_Kernel*.lua at HEAD on a fresh Lua 5.1 runtime; `replace` maps a kernel file's
    basename to the source loaded in its place."""
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    load = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    for path in pre_kernel_files() + kernel_files():
        name = os.path.basename(path)
        if replace and name in replace:
            src = replace[name]
        else:
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
        load(src, "@" + name)()
    return rt


SHARED_REL = os.path.relpath(SHARED, REPO).replace(os.sep, "/")

STOMACH_DAY = r"""
return function()
    local K = NutritionRevamp.kernel
    local s = K.stomach.new()
    local out = {}
    local function vec(t)
        local v = K.vector.new()
        for k, x in pairs(t) do v[k] = x end
        return v
    end
    for m = 1, 240 do
        if m == 5 then K.stomach.ingest(s, vec({ calories = 667, carbs = 80, proteins = 30, lipids = 25, water = 300 }), 1) end
        if m == 7 then K.stomach.ingestLiquid(s, vec({ water = 500 })) end
        if m == 60 then K.stomach.ingestLiquid(s, vec({ water = 280, calories = 210, carbs = 40, proteins = 8 })) end
        if m == 150 then K.stomach.ingestLiquid(s, vec({ water = 250 })) end
        local e = K.stomach.drain(s, 1 / 60)
        out[#out + 1] = string.format("%.17g %.17g %.17g %.17g %.17g", s.liquid, s.buffer.calories, s.buffer.water,
                                      e.water, e.calories)
    end
    return table.concat(out, "\n")
end
"""


def stomach_trace(rt):
    return rt.execute(STOMACH_DAY)()


def test_the_liquid_overlay_drains_as_the_recording_build_did():
    # carries section 4 (c): one synthetic day (a 667 kcal plate, 500 g of water two minutes after it, a 210 kcal shake,
    # water again) through K.stomach.drain under "replay.LIQUID_SOLID_KCAL" at HEAD, and through bcf99149's own
    # NR_Kernel_Stomach.lua (Plan 15 Task 14b's parent): byte-equal; HEAD without the overlay is not
    old = git_show("bcf99149", SHARED_REL + "/NR_Kernel_Stomach.lua")
    then = stomach_trace(kernel_rt({"NR_Kernel_Stomach.lua": old}))
    rt = kernel_rt()
    head = stomach_trace(rt)
    rt.execute(RL._LIQUID_SOLID_KCAL_LUA)
    assert stomach_trace(rt) == then
    assert head != then                                  # the overlay is load-bearing: a plate slowed the old lane


DEFICIT_GRID = [(fm, E, lx, p, S, grow) for fm in (2.5, 8.0, 13.0, 30.0) for E in (-200.0, -900.0, -2400.0)
                for lx in (0.0, 0.4) for p in (0.5, 1.4) for S in (0.0, 12.0) for grow in (0.0, 0.01)]

DEFICIT_CALL = r"""
return function(fm, E, lx, p, S, grow)
    local K = NutritionRevamp.kernel
    local body = { fm = fm, lm = 52, lx = lx }
    local a, b, c = K.partition.deficitLean(body, grow, S, p, E, K.strength.DEFAULTS, 1)
    return string.format("%.17g %.17g %.17g", a, b, c)
end
"""


def deficit_trace(rt):
    f = rt.execute(DEFICIT_CALL)
    return [f(*row) for row in DEFICIT_GRID]


def test_the_fat_ceiling_overlay_is_the_recording_builds_deficit_arm():
    # the deficit arm under "replay.FAT_CEILING" at HEAD against 3a93d51c's own NR_Kernel_Partition.lua (Plan 16 Task 5's
    # parent) over a grid that crosses Alpert's ceiling (a lean body in a deep deficit): equal on every point; HEAD's
    # Forbes split differs where the ceiling bit
    old = git_show("3a93d51c", SHARED_REL + "/NR_Kernel_Partition.lua")
    then = deficit_trace(kernel_rt({"NR_Kernel_Partition.lua": old}))
    rt = kernel_rt()
    head = deficit_trace(rt)
    rt.execute(RL._FAT_CEILING_LUA)
    assert deficit_trace(rt) == then
    assert sum(a != b for a, b in zip(head, then)) > 0


def test_the_bundles_compose_by_build_and_the_study_clock_carries_no_ring_overlay():
    assert set(RL.REPLAY_ONLY) >= {"replay.LIQUID_SOLID_KCAL", "replay.FAT_CEILING"}
    assert RL.PRE_SPLIT == {"replay.FAT_CEILING": 1}
    for small, big in ((RL.WORLD_CLOCK, RL.PRE_FREEZE), (RL.PRE_SPLIT, RL.PRE_FREEZE), (RL.PRE_FREEZE, RL.PRE_LIQUID),
                       (RL.PRE_LIQUID, RL.PRE_PLATE), (RL.PRE_PLATE, RL.PRE_CURVE)):
        assert all(big.get(k) == v for k, v in small.items()), (small, big)
    assert RL.PRE_LIQUID["replay.LIQUID_SOLID_KCAL"] == 1
    assert RL.WORLD_CLOCK == {"replay.WORLD_CLOCK": 1}     # the study oracles' (deficit_oracles.py) test the shipped arm


def test_the_guide_reads_no_replay_only_overlay():
    # spec section 5.1 and carries section 4: the overlays grade an old ring against its own pipeline; the guide draws an
    # old run only where the HEAD replay matches (CLAUDE.md section 5, Plan 14 Task 4), so its tools name none
    for name in ("mod_guide_data.py", "mod_guide_series.py", "vanilla_model.py"):
        with open(os.path.join(REPO, "tools", name), encoding="utf-8") as fh:
            src = fh.read()
        for key in list(RL.REPLAY_ONLY) + ["PRE_LIQUID", "PRE_SPLIT", "PRE_FREEZE", "PRE_PLATE", "PRE_CURVE",
                                           "LIQUID_SOLID_KCAL", "FAT_CEILING"]:
            assert key not in src, (name, key)


def test_x263_needs_the_liquid_overlay():
    # the restored x263 test's checks hold through "replay.LIQUID_SOLID_KCAL"; without it the replay that follows the
    # injected auto-drink misses the ring's liquid lane (HEAD's drink-borne rule empties the water beside a plate faster)
    if not os.path.isdir(X263):
        pytest.skip("the artifact is not in this tree")
    rd = {}
    for name in ("events", "start", "start-stats", "player"):
        with open(os.path.join(X263, name + ".json"), encoding="utf-8") as fh:
            rd[name] = json.load(fh)
    pages = sorted(f for f in os.listdir(X263) if f.startswith("minute-ring-admin-"))
    pages.sort(key=lambda f: int(f.split("-")[-1].split(".")[0]))
    rr, rp = RL.load_ring([os.path.join(X263, f) for f in pages])
    without = {k: v for k, v in RL.PRE_CURVE.items() if k != "replay.LIQUID_SOLID_KCAL"}
    rows, _ = RL.replay_live(rr, rd["events"], rd["start"], paths=rp, user="admin", player=rd["player"],
                             start_stats=rd["start-stats"], sleep_allowed=False, detect_autodrink=True,
                             constants=dict(RL.DEFICIT_11F, **without))
    d = RL.diff(rows, rr, {LIQ: ("abs", 1.0)})
    assert not d["ok"] and d["fields"][LIQ]["max"] > 50.0, d["fields"]


# --- the cold multiplier ------------------------------------------------------------------------------------------

def synthetic_ring(n=180, dtm=1.0, cold=None, key="cold"):
    rows = []
    for i in range(n):
        r = {"s": i + 1, "ev": i + 1, "drained": i, "age": 100.0 + i * dtm / 60.0, "dtM": dtm,
             "hour": int((8 + i * dtm / 60.0) % 24), "min": int((i * dtm) % 60), "on": True}
        if cold is not None:
            r[key] = cold(i)
        rows.append(r)
    return rows


def replay_water(rows, **kw):
    out, be = RL.replay_live(rows, [], None, paths=[WATER, "body.coldMult"], hour_offset=8.0 - 100.0 % 24,
                             sleep_allowed=False, **kw)
    return out, be


def test_a_fed_cold_multiplier_books_the_cold_diuresis():
    # K.fluids.COLD_DIURESIS_LH (0.1 L a game hour) x (coldMult - 1): at 1.05, 5 g of water a game hour more than at 1
    c = 1.05
    on, be = replay_water(synthetic_ring(cold=lambda i: c))
    off, _ = replay_water(synthetic_ring(cold=lambda i: c), ring_cold=False)
    assert be.ring_cold and be.ring_cold[0]["cold"] == c
    assert on[5]["body.coldMult"] == c and off[5]["body.coldMult"] == 1
    # read between two drains well past the first (the first sights the record), one game minute a drain
    a, b = 20, 170
    extra = (off[b][WATER] - on[b][WATER]) - (off[a][WATER] - on[a][WATER])
    hours = on[b]["age"] - on[a]["age"]
    assert extra == pytest.approx(100.0 * (c - 1) * hours, rel=1e-6)


def test_a_ring_without_the_cold_multiplier_replays_as_before():
    rows = synthetic_ring()
    auto, be = replay_water(rows)
    off, _ = replay_water(rows, ring_cold=False)
    assert be.ring_cold == [] and not RL.ring_carries_cold(rows)
    assert [r[WATER] for r in auto] == [r[WATER] for r in off]


def test_the_cold_event_carries_the_next_rows_value_the_field_first():
    rows = synthetic_ring(n=6, cold=lambda i: 1.0 + 0.001 * i)
    ev = RL.ring_cold_events(rows)
    assert [(e["s"], e["cold"]) for e in ev] == [(1, 1.001), (2, 1.002), (3, 1.003), (4, 1.004), (5, 1.005)]
    assert all(e["kind"] == "activity" and e["label"] == RL.RING_ACTIVITY_LABEL for e in ev)
    path = synthetic_ring(n=4, cold=lambda i: 1.0 + 0.01 * i, key="body.coldMult")
    assert [(e["s"], e["cold"]) for e in RL.ring_cold_events(path)] == [(1, 1.01), (2, 1.02), (3, 1.03)]
    both = synthetic_ring(n=3, cold=lambda i: 1.5, key="body.coldMult")
    for r in both:
        r["cold"] = 1.2
    assert [e["cold"] for e in RL.ring_cold_events(both)] == [1.2]       # the field before the path; no repeat
    gap = synthetic_ring(n=5, cold=lambda i: 1.0 + 0.001 * i)
    gap[2]["on"] = False
    assert [e["s"] for e in RL.ring_cold_events(gap)] == [1, 4]          # no event across an offline row


def test_the_cold_feed_reads_only_the_cold_keys():
    # the feed is an input, never an output: every other field of every row may change and the events stay
    rows = synthetic_ring(n=30, cold=lambda i: 1.0 + 0.0001 * (i % 7))
    want = RL.ring_cold_events(rows)
    for i, r in enumerate(rows):
        for k in ("HUNGER", "THIRST", WATER, "body.met", "fluids.dehydPct", "stomach.liquid", "rate", "exe"):
            r[k] = (i * 7919 % 101) / 7.0
    assert RL.ring_cold_events(rows) == want


def test_an_activity_event_naming_cold_is_refused_while_the_ring_feeds_it():
    rows = synthetic_ring(cold=lambda i: 1.01)
    with pytest.raises(ValueError, match="cold"):
        RL.replay_live(rows[:10], [{"s": 3, "kind": "activity", "cold": 1.2}], None, paths=[WATER],
                       hour_offset=8.0 - 100.0 % 24, sleep_allowed=False)


def load_ring(run):
    pages = sorted(glob.glob(os.path.join(run, "minute-ring-admin-*.json")),
                   key=lambda f: int(f.rsplit("-", 1)[1].split(".")[0]))
    return RL.load_ring(pages)


def ring_start(ring, rp, h1):
    """x456 and x457 logged no start record (their drivers graded the ring alone): the start is the ring's first row's
    record paths over the H1 read's (the body's constant fields: fm, lx, sex, firstSeen), stamped one game minute before
    that row (the drain that left it), and the stand-in's stats at the row's."""
    r0 = ring[0]
    vals = dict(h1)
    vals.update({p: r0[p] for p in rp if not p.startswith("_G") and p in r0})
    for stamp in ("lastSeen", "kineticsAge", "satiety.t", "nutrients.lastAgeH", "body.lastAgeH"):
        vals[stamp] = r0["age"] - 1.0 / 60.0
    return RL.nest(vals), {k: r0[k] for k in ("HUNGER", "THIRST", "FATIGUE")}


def x45_events(ring, doc):
    """The run's inputs as replay events. x456's record.set of fluids.water, keyed to the last ring row read before the
    reply's age (the set showed on that row's read). x457's trait.set arms, keyed to the row before the first that
    reads the arm's applied basal scale (the scale is the mod's, read only to place the trait's minute; the replay
    derives its own from the trait)."""
    events = []
    for a in doc.get("sets") or []:
        s = [r["s"] for r in ring if r["age"] < a["age"] - 1e-9][-1]
        assert next(r for r in ring if r["s"] == s)[a["path"]] == float(a["value"])
        events.append({"s": s, "kind": "setpath", "path": a["path"], "value": float(a["value"])})
    scale = "_G.NutritionRevamp.server.nutrients.fctx.basalScale"
    held, prev = set(), None
    for i, r in enumerate(ring):
        v = r.get(scale)
        if prev is not None and v != prev:
            want = {1.5: {"HIGH_THIRST"}, 0.5: {"LOW_THIRST"}, 1: set()}[v]
            s = ring[i - 1]["s"]
            events += [{"s": s, "kind": "trait", "trait": t, "on": False} for t in sorted(held - want)]
            events += [{"s": s, "kind": "trait", "trait": t, "on": True} for t in sorted(want - held)]
            held = want
        prev = v
    return events


@pytest.mark.parametrize("run,doc,traits", [(X456, "water.json", 0), (X457, "thirst.json", 4)])
def test_the_x456_and_x457_rings_replay_thirst_with_the_cold_multiplier_fed(run, doc, traits):
    # #3947: the live body water ran 0.24-0.53 g a game hour under the replay's, the cold diuresis of a coldMult a little
    # over 1 the stand-in answered as 1. Fed from the rings' body.coldMult path, THIRST holds within 0.002 and the body
    # water within 0.5 g on every row (the start's one-minute stamp sets the first rows' 0.06-0.16 g); answered as 1,
    # the water drifts past 3 g. Both runs at a97fec05, before the seed plate, the liquid change, the freeze, the body
    # clock and the deficit split: replayed on PRE_PLATE, their own pipeline (sleep off; an empty stomach throughout)
    if not os.path.isdir(run):
        pytest.skip("the artifact is not in this tree")
    with open(os.path.join(run, doc), encoding="utf-8") as fh:
        D = json.load(fh)
    ring, rp = load_ring(run)
    assert "body.coldMult" in rp and RL.ring_carries_cold(ring) and not any("cold" in r for r in ring)
    start, stats = ring_start(ring, rp, D["checks"]["H"]["h1_record"]["values"])
    events = x45_events(ring, D)
    assert len([e for e in events if e["kind"] == "trait"]) == traits
    kw = dict(paths=rp, sleep_allowed=False, start_stats=stats, constants=RL.PRE_PLATE)
    on, be = RL.replay_live(ring, events, start, **kw)
    off, _ = RL.replay_live(ring, events, start, ring_cold=False, **kw)
    assert len(be.ring_cold) > 100
    tol = {"THIRST": ("abs", 0.002), WATER: ("abs", 0.5)}
    d_on, d_off = RL.diff(on, ring, tol), RL.diff(off, ring, tol)
    assert d_on["ok"], d_on["findings"][:3]
    assert d_on["fields"]["THIRST"]["n"] > 600 and d_on["fields"]["THIRST"]["max"] < 0.0003
    assert not d_off["ok"] and d_off["fields"][WATER]["max"] > 3.0, d_off["fields"]


# --- drinks sip by sip --------------------------------------------------------------------------------------------

def test_the_drink_span_follows_the_action_length_and_the_day():
    w = {"kind": "drink", "fluid": "Water", "litres": 0.5, "whole": True}
    assert RL.drink_span_h(w, 1) * 60 == pytest.approx(14.72)          # 9.2 s at 0.625 s a game minute (carries 1)
    assert RL.drink_span_h(w, 3) * 60 == pytest.approx(3.68)
    assert RL.drink_span_h(w, 4) * 60 == pytest.approx(2.4533333)      # the fixture's 90-minute day, #0893's 3.75 s
    assert RL.drink_span_h(w, 4, speed=5.0) * 60 == pytest.approx(12.266667)
    assert RL.drink_span_h(dict(w, maxTime=160), 1) * 60 == pytest.approx(5.12)
    assert RL.DAY_LENGTH_REAL_MIN[6] == 180.0 and RL.DAY_LENGTH_REAL_MIN[26] == 1380.0
    with pytest.raises(ValueError, match="maxTime"):
        RL.drink_span_h({"kind": "drink", "fluid": "CowMilk", "litres": 0.3}, 1)
    with pytest.raises(ValueError, match="DayLength"):
        RL.drink_span_h(w, 0)


def test_drink_units_follow_vanilla_new_and_adjust_max_time():
    # ISDrinkFluidAction.new: 460 with no HungerChange, 160 for a popcan whatever the fluid; ISBaseTimedAction
    # .adjustMaxTime: x (1 + Unhappy / 4) x (1 + Drunk / 4) x getTimedActionTimeModifier (no hand pain: ignoreHandsWounds)
    w = {"kind": "drink", "fluid": "Water", "litres": 0.5}
    assert RL.drink_units(w) == 460.0
    assert RL.drink_units(dict(w, fluid="CarbonatedWater", eatType="popcan")) == 160.0
    assert RL.drink_units({"fluid": "Cola", "eatType": "popcan"}) == 160.0
    assert RL.drink_units(dict(w, maxTime=232)) == 232.0
    assert RL.drink_units(dict(w, unhappy=2)) == pytest.approx(690.0)
    assert RL.drink_units(dict(w, drunk=4)) == pytest.approx(920.0)
    assert RL.drink_units(dict(w, unhappy=1, drunk=1, timeMod=1.2)) == pytest.approx(460 * 1.25 * 1.25 * 1.2)
    assert RL.drink_units(dict(w, maxTime=1, drunk=4)) == 1.0           # adjustMaxTime leaves a length of 1 alone
    for bad in (dict(w, unhappy=5), dict(w, drunk=-1), dict(w, timeMod=0), dict(w, maxTime=0)):
        with pytest.raises(ValueError):
            RL.drink_units(bad)


def test_only_a_drink_flagged_whole_spreads():
    evs = [{"s": 10, "kind": "drink", "fluid": "Water", "litres": 0.5, "whole": True},        # whole, unlabelled
           {"s": 20, "kind": "drink", "fluid": "Water", "litres": 0.5, "label": "W", "whole": True},
           {"s": 25, "kind": "drink", "fluid": "Water", "litres": 0.5, "label": "P"},         # one sip row, unflagged
           {"s": 30, "kind": "drink", "fluid": "Water", "litres": 0.1, "label": "X"},         # a ring's sip rows
           {"s": 31, "kind": "drink", "fluid": "Water", "litres": 0.1, "label": "X"},
           {"s": 40, "kind": "drink", "vec": {"water": 200.0}, "label": "autodrop"},          # the writer's sip
           {"s": 70, "kind": "eat", "vec": {"calories": 10.0}}]
    assert RL.whole_drinks(evs) == [0, 1]
    with pytest.raises(ValueError, match="per-sip"):                    # never a per-sip-logged drink
        RL.whole_drinks(evs + [{"s": 32, "kind": "drink", "fluid": "Water", "litres": 0.1, "label": "X",
                                "whole": True}])
    with pytest.raises(ValueError, match="vec"):
        RL.whole_drinks([{"s": 1, "kind": "drink", "vec": {"water": 1.0}, "whole": True}])


def test_spread_drinks_lands_the_whole_volume_over_the_span():
    ages = RL.synthetic_ages(60, 0.0, 1.0)
    ev = {"minute": 10, "kind": "drink", "fluid": "Water", "litres": 0.5, "label": "W", "whole": True}
    out, rep = RL.spread_drinks([ev], ages, None, 0.0, day_length=1)
    assert [e["minute"] for e in out] == list(range(10, 25))           # 14.72 game minutes: 15 drains
    assert sum(e["litres"] for e in out) == pytest.approx(0.5, abs=1e-12)
    assert all("whole" not in e and e["label"] == "W" for e in out)     # a sip is never spread again
    assert RL.whole_drinks(out) == []
    assert rep == [{"label": "W", "step": 10, "steps": 15, "litres": 0.5, "spanM": pytest.approx(14.72)}]
    four, _ = RL.spread_drinks([ev], ages, None, 0.0, day_length=4)
    assert [e["minute"] for e in four] == [10, 11, 12]
    real, _ = RL.spread_drinks([ev], ages, None, 0.0, day_length=27)    # a real-time day: inside its own minute
    assert [(e["minute"], e["litres"]) for e in real] == [(10, pytest.approx(0.5))]
    same, rep = RL.spread_drinks([ev], ages, None, 0.0, day_length=None)
    assert same == [ev] and rep == []
    unflagged = dict(ev)
    del unflagged["whole"]
    kept, rep = RL.spread_drinks([unflagged], ages, None, 0.0, day_length=1)
    assert kept == [unflagged] and rep == []


def test_spread_drinks_keys_an_s_or_age_drink_from_its_own_step():
    ages = [100.0 + i / 60.0 for i in range(40)]
    seqs = list(range(1, 41))
    w = {"kind": "drink", "fluid": "Water", "litres": 0.3, "whole": True}
    by_s, _ = RL.spread_drinks([dict(w, s=5)], ages, seqs, 99.9, 4)
    # step 4 is ring row s 5; the drink starts at that row's age (a minute-keyed one at its step's start), so its
    # 2.45 game minutes reach the drains of rows s 5 to s 8
    assert [e["minute"] for e in by_s] == [4, 5, 6, 7]
    by_age, _ = RL.spread_drinks([dict(w, age=ages[7] - 0.001)], ages, seqs, 99.9, 4)
    assert by_age[0]["minute"] == 7
    late, _ = RL.spread_drinks([dict(w, s=40)], ages, seqs, 99.9, 1)
    assert [e["minute"] for e in late] == [39] and late[0]["litres"] == pytest.approx(0.3)   # past the clock: the last


def test_a_replayed_drink_spreads_its_landing():
    # spec section 4.3: a lone 0.5 L water after a plate, on a one-minute clock at DayLength 1, reaches the liquid lane
    # over 15 drains, not one; the lane's peak is lower and the water landed is the same
    ev = [{"minute": 5, "kind": "meal", "size": 667.0},
          {"minute": 6, "kind": "drink", "fluid": "Water", "litres": 0.5, "whole": True}]
    whole, _ = RL.replay_arm(ev, minutes=60, paths=[LIQ, "stomach.buffer.water"], sleep_allowed=False,
                             constants=RL.WORLD_CLOCK)
    spread, be = RL.replay_arm(ev, minutes=60, paths=[LIQ, "stomach.buffer.water"], sleep_allowed=False,
                               constants=RL.WORLD_CLOCK, day_length=1)
    assert be.spread[0]["steps"] == 15
    rises_whole = [k for k in range(1, 60) if whole[k][LIQ] > whole[k - 1][LIQ] + 1e-9]
    rises_spread = [k for k in range(1, 60) if spread[k][LIQ] > spread[k - 1][LIQ] + 1e-9]
    assert rises_whole == [6] and rises_spread == list(range(6, 21))
    assert max(r[LIQ] for r in spread) < max(r[LIQ] for r in whole) - 100.0
    landed = [e for e in be.eats if e["kind"] == "drink"]
    assert len(landed) == 15


def test_replay_live_spreads_a_whole_drink_on_the_ring_clock_and_leaves_sip_rows():
    # end to end through replay_live (review finding 8): a flagged 0.5 L water at ring row s 10 on a one-minute ring
    # at DayLength 1 lands over 15 drains; the same volume logged as two sip rows under one label lands as logged on
    # those two rows at the same day length, and flagging one of those sip rows whole is refused
    rows = synthetic_ring(n=60)
    flagged = [{"s": 10, "kind": "drink", "fluid": "Water", "litres": 0.5, "label": "W", "whole": True}]
    kw = dict(paths=[LIQ], hour_offset=8.0 - 100.0 % 24, sleep_allowed=False, day_length=1)
    out, be = RL.replay_live(rows, flagged, None, **kw)
    # an s-keyed drink starts at its row's age (an arm's minute-keyed one at its step's start), so its 14.72 game
    # minutes reach a sixteenth drain on a one-minute ring
    assert be.spread == [{"label": "W", "step": 9, "steps": 16, "litres": 0.5, "spanM": pytest.approx(14.72)}]
    landed = [e for e in be.eats if e["kind"] == "drink"]
    assert len(landed) == 16 and sum(e["kcal"] or 0 for e in landed) == 0
    rises = [k for k in range(1, len(out)) if out[k][LIQ] > out[k - 1][LIQ] + 1e-9]
    assert rises == list(range(9, 25))                                  # drains 9-24: ring rows s 10 to s 25
    sips = [{"s": 10, "kind": "drink", "fluid": "Water", "litres": 0.25, "label": "X"},
            {"s": 11, "kind": "drink", "fluid": "Water", "litres": 0.25, "label": "X"}]
    logged, be2 = RL.replay_live(rows, sips, None, **kw)
    assert be2.spread == [] and len([e for e in be2.eats if e["kind"] == "drink"]) == 2
    with pytest.raises(ValueError, match="per-sip"):
        RL.replay_live(rows, [dict(sips[0], whole=True), sips[1]], None, **kw)


def test_a_trait_the_stand_in_lacks_is_refused():
    # review finding 7: ev_trait once ignored an unknown trait silently; a known one sets the stand-in's trait
    rows = synthetic_ring(n=8)
    with pytest.raises(ValueError, match="CharacterTrait has no"):
        RL.replay_live(rows, [{"s": 3, "kind": "trait", "trait": "NOT_A_TRAIT"}], None, paths=[WATER],
                       hour_offset=8.0 - 100.0 % 24, sleep_allowed=False)
    scale = "_G.NutritionRevamp.server.nutrients.fctx.basalScale"
    out, be = RL.replay_live(rows, [{"s": 3, "kind": "trait", "trait": "HIGH_THIRST"}], None, paths=[scale],
                             hour_offset=8.0 - 100.0 % 24, sleep_allowed=False)
    assert be.p.st.traits[be.G.CharacterTrait.HIGH_THIRST] is True
    assert [r.get(scale) for r in out[1:4]] == [1, 1.5, 1.5]            # the drain of ring row s 3 is replay row 2


def test_a_live_rings_drinks_are_left_as_logged():
    # x452b's three 0.5 L drinks are logged per ring row their sips landed on (15-16 rows each, one label each), so
    # the replay lands them as logged at any day length
    if not os.path.isdir(X452B):
        pytest.skip("the artifact is not in this tree")
    with open(os.path.join(X452B, "events.json"), encoding="utf-8") as fh:
        events = json.load(fh)
    assert len([e for e in events if e.get("kind") == "drink"]) == 47
    assert RL.whole_drinks(events) == []
    out, rep = RL.spread_drinks(events, [0.0, 1.0], None, None, day_length=1)
    assert out == events and rep == []
