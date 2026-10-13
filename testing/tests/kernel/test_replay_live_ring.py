"""tools/replay_live.py against the harness's own minute ring (Plan 11f Task 2), offline end to end.

A stand-in "live" server (ServerReplay A: the mod's server adapters on server_host with the golden stand-ins) runs with
the harness's H1 and H2 blocks loaded beside it (as test_harness_minute_ring.py loads them), its ring armed on a few
record paths. Its clock steps unevenly (1, 2, 0.5, 3 game-minute gaps), so the ring's dtM is not 1. Between drains it
eats a TKX_StudyFoods meal, drinks water, falls asleep and wakes, and its engine-owned NICOTINE_WITHDRAWAL moves with
no event logged. The slot file line A's store would write (K.store.inputsOnly through K.json.encode at the store's
own fmt) is the start record; the ring page read through `minute.ring admin read` is the ring. The replay of that
page and the event log (mode live) must then match every ring row it is compared with, HUNGER, satiety.M,
body.energyState and satiety.L within 1e-9 (the slot line keeps 14 digits, tostring's %.14g), skipping exactly the
rows an event landed before; a replay that compared drain k with ring row k (the wrong phase), or stepped a fixed
1-minute clock, or fed no NICOTINE_WITHDRAWAL, fails. The harness is never a kernel file, so the coverage gate is
untouched."""
import json
import os
import sys

import pytest

from .server_host import REPO
from .test_harness_minute_ring import CORE, SERVER, STUB_TK, load, section

sys.path.insert(0, os.path.join(REPO, "tools"))
import replay_live as RL  # noqa: E402

PATHS = ("satiety.M", "satiety.L", "body.energyState", "stomachFill", "satiety.nicH", "body.trail.kcal.3",
         "_G.NutritionRevamp.server.intake.stats.landed")
A0 = 1000.0                       # world age at the warm-up's start (hours)
WARM = 40                         # warm-up minutes before the slot line is taken
GAPS = [1, 2, 0.5, 1, 3] * 24     # game minutes between ring events: 120 rows, dtM uneven
OFFSET = 7.0                      # the clock's hour at world age 0 (#2890)

SLOT = r"""
function(u)
    local NR = NutritionRevamp
    local K = NR.kernel
    return K.json.encode({ gen = 1, rec = K.store.inputsOnly(NR.server.store.records[u]), done = true },
                         NR.server.store.file.fmt)
end
"""


def live_run():
    """(the slot line, the ring page as JSON, the event log, the nicotine moves) of the stand-in live server."""
    a = RL.ServerReplay(start=None, user="admin", hour_offset=OFFSET,
                        stats={"HUNGER": 0.3, "THIRST": 0.2, "FATIGUE": 0.1, "NICOTINE_WITHDRAWAL": 0.0})
    age = A0
    for _ in range(WARM):
        age += 1 / 60
        a.step(age)
    slot = a.rt.eval(SLOT)("admin")
    a.rt.execute(STUB_TK)
    a.rt.execute("TK.now = function() return 0 end")
    load(a.h, section(CORE, "-- ==== Plan 11f Task 1 additions (H1)"), "@PZTestKit_Core.lua")
    load(a.h, section(SERVER, "-- ==== Plan 11f Task 1 additions (H2)"), "@PZTestKit_Server.lua")
    TK = a.G.TK
    armed = TK.commands["minute.ring"](a.rt.table("admin", "start", *PATHS))
    assert armed.ok is True, armed
    events = []
    ages = []
    mid_slot = None
    for i, gap in enumerate(GAPS):
        nxt = age + gap / 60
        ages.append(nxt)
        a.step(nxt)
        if i == 20:
            mid_slot = a.rt.eval(SLOT)("admin")             # a slot line taken mid-ring, after this drain
        mid = nxt + min(GAPS[(i + 1) % len(GAPS)], 0.5) / 120     # after this drain, before the next event
        ev = None
        if i == 10:
            ev = {"age": mid, "kind": "eat", "food": "TKX.Mixed650"}
        elif i == 30:
            ev = {"age": mid, "kind": "drink", "fluid": "Water", "litres": 0.3}
        elif i == 50:
            ev = {"age": mid, "kind": "sleep", "asleep": True}
        elif i == 80:
            ev = {"age": mid, "kind": "sleep", "asleep": False}
        elif i == 90:
            ev = {"age": mid, "kind": "eat", "food": "TKX.SnackP", "frac": 0.5}
        if ev is not None:
            a.apply(ev, ev["age"])
            events.append(ev)
        if i == 60:
            a.p.sv.NICOTINE_WITHDRAWAL = 0.3           # the engine's own rise: no event is logged
        if i == 100:
            a.p.sv.NICOTINE_WITHDRAWAL = 0.05          # a smoke's fall
        age = nxt
    page = TK.commands["minute.ring"](a.rt.table("admin", "read"))
    assert page.ok is True and page.rows == len(GAPS), page
    doc = RL.to_py(a.lua51, TK.results[page.result])
    a.mid_slot = mid_slot
    return slot, json.loads(json.dumps(doc)), events, a


def s_keyed(e, rows):
    """The event keyed by the first ring row at or after its age (the row a landing count first shows)."""
    out = {k: v for k, v in e.items() if k != "age"}
    out["s"] = next(r["s"] for r in rows if r["age"] >= e["age"])
    return out


@pytest.fixture(scope="module")
def live():
    return live_run()


def test_the_ring_page_is_the_harness_format_and_its_dtm_is_uneven(live):
    slot, doc, events, _ = live
    rows, paths = RL.load_ring([doc])
    assert paths == list(PATHS) and len(rows) == len(GAPS)
    assert [r["s"] for r in rows] == list(range(1, len(GAPS) + 1))
    dts = [round(r["dtM"], 9) for r in rows[1:]]
    assert dts == [float(g) for g in GAPS[1:]]
    assert RL.estimate_offset(rows) == OFFSET


def test_the_live_replay_matches_every_ring_row_but_those_an_event_landed_before(live):
    slot, doc, events, _ = live
    rows, paths = RL.load_ring([doc])
    out, be = RL.replay_live(rows, events, slot, ring_paths=paths, sleep_allowed=True)
    by_s = {r["s"]: r for r in rows}
    compared = 0
    for r in out:
        if r["s"] not in by_s:
            continue
        if r["between"]:
            continue
        live_row = by_s[r["s"]]
        for f in ("HUNGER", "THIRST", "satiety.M", "satiety.L", "body.energyState", "stomachFill", "satiety.nicH"):
            assert r[f] == pytest.approx(live_row[f], rel=1e-9, abs=1e-12), (r["s"], f, r[f], live_row[f])
        assert r["age"] == live_row["age"] and r["dtM"] == live_row.get("dtM")
        compared += 1
    skipped = [r["s"] for r in out if r["between"]]
    assert len(skipped) == len(events)                 # each event lands before exactly one compared row
    assert compared == len(rows) - 1 - len(skipped)
    d = RL.diff(out, rows)
    assert d["ok"] and d["skipped"] == skipped and d["fields"]["HUNGER"]["n"] == compared, d
    assert [e["kind"] for e in be.eats] == ["eat", "drink", "eat"]
    assert be.eats[0]["kcal"] == pytest.approx(650.0)


def test_the_eat_count_path_shows_each_landing_in_the_row_after_it(live):
    slot, doc, events, _ = live
    rows, _ = RL.load_ring([doc])
    key = "_G.NutritionRevamp.server.intake.stats.landed"
    rises = [rows[i]["s"] for i in range(1, len(rows)) if rows[i].get(key, 0) > rows[i - 1].get(key, 0)]
    eat_s = []
    for e in events:
        if e["kind"] == "eat":
            eat_s.append(next(r["s"] for r in rows if r["age"] >= e["age"]))
    assert rises == eat_s and len(rises) == 2       # IN.readAfterAndLand's count rises in the row after each eat
    # an s-keyed log (the landing the ring shows) replays as the age-keyed one does
    a, _ = RL.replay_live(rows, events, slot, ring_paths=RL.load_ring([doc])[1], sleep_allowed=True)
    b, _ = RL.replay_live(rows, [s_keyed(e, rows) for e in events], slot, ring_paths=RL.load_ring([doc])[1], sleep_allowed=True)
    assert [r["between"] for r in a] == [r["between"] for r in b]
    for ra, rb in zip(a, b):
        assert rb["satiety.M"] == pytest.approx(ra["satiety.M"], rel=1e-9)


def test_a_wrong_phase_or_a_fixed_clock_or_no_feed_is_caught(live):
    slot, doc, events, _ = live
    rows, paths = RL.load_ring([doc])
    out, _ = RL.replay_live(rows, events, slot, ring_paths=paths, sleep_allowed=True)
    # drain k against ring row k: the wrong phase moves HUNGER past the tolerance somewhere
    wrong = [dict(r, s=r["s"] - 1) for r in out]
    tight = {"satiety.M": ("rel", 1e-9), "HUNGER": ("abs", 1e-9)}
    assert not RL.diff(wrong, rows, tight)["ok"]
    # a fixed one-minute clock in place of the ring's ages (the events keyed by the row that shows them)
    fixed = [dict(r, age=rows[0]["age"] + i / 60) for i, r in enumerate(rows)]
    out2, _ = RL.replay_live(fixed, [s_keyed(e, rows) for e in events], slot, ring_paths=paths, sleep_allowed=True)
    assert not RL.diff(out2, rows, tight)["ok"]
    # no NICOTINE_WITHDRAWAL fed: the anchor and the factor diverge after the engine's moves
    out3, _ = RL.replay_live(rows, events, slot, ring_paths=paths, feed=(), sleep_allowed=True)
    assert not RL.diff(out3, rows, {"satiety.nicH": ("abs", 1e-9), "HUNGER": ("abs", 1e-9)})["ok"]


def test_mode_arm_on_the_rings_clock_with_the_same_events_reproduces_the_live_mode(live):
    slot, doc, events, _ = live
    rows, paths = RL.load_ring([doc])
    out, _ = RL.replay_live(rows, events, slot, ring_paths=paths, feed=(), sleep_allowed=True)
    sa = json.loads(slot)["rec"]["satiety"]["t"]
    use = [r for r in rows if r["age"] > sa + 1e-9]
    arm, _ = RL.replay_arm(events, start=slot, ring_rows=use, paths=paths, hour_offset=OFFSET,
                           stats={k: use[0][k] for k in RL.STATS if use[0].get(k) is not None})
    for a, b in zip(out, arm):
        assert a["HUNGER"] == b["HUNGER"] and a["satiety.M"] == b["satiety.M"]


def test_a_start_record_taken_mid_ring_drops_the_rows_and_events_it_holds(live):
    slot, doc, events, a = live
    rows, paths = RL.load_ring([doc])
    sa = json.loads(a.mid_slot)["rec"]["satiety"]["t"]
    out, be = RL.replay_live(rows, events, a.mid_slot, ring_paths=paths, sleep_allowed=True)
    assert out[0]["s"] == next(r["s"] for r in rows if r["age"] > sa + 1e-9) + 1 == 23   # row 21 is the slot's own minute
    assert be.dropped == [e for e in events if e["age"] <= sa] and len(be.dropped) == 1
    d = RL.diff(out, rows, {"HUNGER": ("abs", 1e-9), "satiety.M": ("rel", 1e-9), "body.energyState": ("abs", 1e-9)})
    assert d["ok"] and d["fields"]["HUNGER"]["n"] > 80, d
    out2, be2 = RL.replay_live(rows, [s_keyed(e, rows) for e in events], a.mid_slot, ring_paths=paths, sleep_allowed=True)
    assert len(be2.dropped) == 1 and [r["HUNGER"] for r in out2] == [r["HUNGER"] for r in out]


def test_a_drink_lands_in_the_liquid_lane_and_a_typed_vector_eat_books_monotony():
    rp = RL.ServerReplay(start={"username": "admin", "firstSeen": 99.0, "lastSeen": 99.0,
                                "satiety": {"M": 10.0, "S": 0, "L": 0, "t": 99.0}})
    rp.apply({"kind": "drink", "fluid": "Water", "litres": 0.3}, 100.0)
    st = rp.record().stomach
    assert st.buffer.water == 0 and st.liquid > 250
    rp.apply({"kind": "drink", "vec": {"water": 100.0}}, 100.0)
    assert st.buffer.water == 0
    v = {"calories": 450.0, "proteins": 16.875, "carbs": 56.25, "lipids": 17.5, "water": 200.0}
    rp.apply({"kind": "eat", "vec": v, "fullType": "TKX.Typed"}, 100.0)
    rp.apply({"kind": "eat", "vec": v, "fullType": "TKX.Typed"}, 124.0)
    assert rp.record().monotony.t["TKX.Typed"].n == pytest.approx(1 + 2 ** (-24 / 72.0))
    assert rp.eats[-1]["boredom"] == 0                                   # no add at the eat (Plan 11f Task 9b)
    assert rp.K.monotony.target(rp.record().monotony, 124.0)[0] == pytest.approx(4.3 * 2 ** (-24 / 72.0))
    assert st.buffer.water == pytest.approx(400.0)


# x260b's reconnect (Plan 11f Task 3, ruling S0-3): rows 1-59 offline, row 60 online with no record (the first sight,
# which live drained), row 61 on. The committed artifact is read from the working tree.
X260B = os.path.join(REPO, "testing", "artifacts", "x260b-20261010-111433")


def _x260b():
    pages = [os.path.join(X260B, f) for f in ("minute-ring-admin-1.json", "minute-ring-admin-100.json")]
    rows, paths = RL.load_ring(pages)
    with open(os.path.join(X260B, "start.json"), encoding="utf-8") as fh:
        start = json.load(fh)
    with open(os.path.join(X260B, "start-stats.json"), encoding="utf-8") as fh:
        stats = json.load(fh)
    with open(os.path.join(X260B, "player.json"), encoding="utf-8") as fh:
        player = json.load(fh)
    return rows, paths, start, stats, player


@pytest.mark.skipif(not os.path.isdir(X260B), reason="the x260b artifact is not in this tree")
def test_x260b_the_reconnects_online_first_sight_row_drains_with_no_lag():
    # Plan 11g Task 4: the artifact's ring was taken on the P model, so satiety.P and HUNGER are no longer replayed
    # (the P model's replay held satiety.P within 1e-3 and HUNGER within DEFAULT_TOL: this test at 0f14044f). The first
    # sight's drain is read off the model-independent state, the energy state, the exercise lag and the stomach fill;
    # HUNGER's fidelity under M is tested on x361's ring (testing/tests/test_x36_gut_lib.py::test_the_x361_ring_replays_within_the_default_tolerances, Plan 11g Task 8)
    rows, paths, start, stats, player = _x260b()
    first = next(r for r in rows if r.get("on") is not False)
    assert first.get("norec") and not RL.offline_row(first)
    out, be = RL.replay_live(rows, [], start, paths=paths, user="admin", player=player, start_stats=stats, sleep_allowed=True,
                             constants=RL.DEFICIT_11F)          # the ring's build's deficit drive (Plan 11g Task 7)
    by_s = {r["s"]: r for r in out}
    assert by_s[first["s"]].get("offline") is True             # replay row k is labelled with ring row k + 1's s:
    assert by_s[first["s"] + 1].get("offline") is None         # the first-sight minute is drained, not offline
    tol = {"body.energyState": RL.DEFAULT_TOL["body.energyState"], "satiety.L": RL.DEFAULT_TOL["satiety.L"],
           "stomachFill": ("abs", 1e-6)}                       # the ring rows read about 3e-9 off
    d = RL.diff(out, rows, tol)
    assert d["ok"], d["findings"][:3]
    assert all(d["fields"][f]["n"] > 30 for f in tol)
    h = RL.diff(out, rows, {"HUNGER": RL.DEFAULT_TOL["HUNGER"]})["fields"]["HUNGER"]
    assert h["n"] == 41 and round(h["max"], 4) == 0.0097, h                 # the P ring against the refit M (Plan 11g Task 6c fix 2): a reading (0.0096 under fix 1's refit, 0.0229 under Task 6c's fit, 0.0069 under the gut stage's fit, 0.0223 under its provisional constants), at DEFICIT_11F, the ring's deficit drive (Plan 11g Task 7)
