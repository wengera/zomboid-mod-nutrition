"""tools/replay_live.py fix round 1 (Plan 11f Task 2): the ring's own bookkeeping (s, ev, drained, on, norec), the
start record's read age, the event fraction contract and the replay's independence from the ring's outputs.

Each live run is a stand-in server (ServerReplay with the harness's H1 and H2 blocks loaded beside it, as
test_replay_live_ring.py builds it) whose ring is the replay's input. The classes are checked on the replay of that
ring: an offline window is not drained and the reconnect drain is the mod's own 60-minute clamp; a missing row (a jump
in s), a missed sample (a jump in ev) and a long minute (dtM above 2.05, ruling S0-1) are marked gap and stepped by the real age
delta; a row whose drain had not advanced is suspect and not graded; an eat between the record's last drain and its
read is dropped by start_read_age; and a ring whose every output is scaled replays bit-identically while the diff
fails.
"""
import json
import os
import sys

import pytest

from .server_host import REPO
from .test_harness_minute_ring import CORE, SERVER, STUB_TK, load, section
from .test_replay_live_ring import SLOT, live_run

sys.path.insert(0, os.path.join(REPO, "tools"))
import replay_live as RL  # noqa: E402

PATHS = ("satiety.M", "satiety.S", "satiety.L", "body.energyState", "stomachFill", "satiety.nicH",
         "body.lastAgeH")
TIGHT = {"HUNGER": ("abs", 1e-9), "satiety.M": ("rel", 1e-9), "satiety.L": ("rel", 1e-9),
         "body.energyState": ("abs", 1e-9), "stomachFill": ("rel", 1e-9)}
OUTPUTS = ("HUNGER", "satiety.M", "satiety.S", "satiety.L", "body.energyState", "stomachFill", "satiety.nicH",
           "THIRST", "FATIGUE", "BOREDOM", "UNHAPPINESS")


def mini_live(n, actions=None, gaps=None, a0=500.0, warm=30):
    """A stand-in live server stepped n ring minutes (gaps[i] game minutes before minute i, default 1) after `warm`
    unringed minutes. actions[i](a, age) runs after drain i and may return an event (logged). Returns
    (slots, page rows, ring paths, events, the stand-in), slots[i] the slot line an action took."""
    a = RL.ServerReplay(start=None, user="admin", hour_offset=7.0,
                        stats={"HUNGER": 0.3, "THIRST": 0.2, "FATIGUE": 0.1, "NICOTINE_WITHDRAWAL": 0.0})
    age = a0
    for _ in range(warm):
        age += 1 / 60
        a.step(age)
    a.rt.execute(STUB_TK)
    a.rt.execute("TK.now = function() return 0 end")
    load(a.h, section(CORE, "-- ==== Plan 11f Task 1 additions (H1)"), "@PZTestKit_Core.lua")
    load(a.h, section(SERVER, "-- ==== Plan 11f Task 1 additions (H2)"), "@PZTestKit_Server.lua")
    TK = a.G.TK
    TK.MR.PAGE = 4320
    assert TK.commands["minute.ring"](a.rt.table("admin", "start", *PATHS)).ok is True
    a.slots = {}
    events = []
    for i in range(n):
        age += (gaps[i] if gaps else 1) / 60
        a.step(age)
        fn = (actions or {}).get(i)
        if fn is not None:
            ev = fn(a, age)
            if ev is not None:
                events.append(ev)
    page = TK.commands["minute.ring"](a.rt.table("admin", "read"))
    assert page.ok is True and page.rows == n, page
    doc = json.loads(json.dumps(RL.to_py(a.lua51, TK.results[page.result])))
    rows, paths = RL.load_ring([doc])
    return a.slots, rows, paths, events, a


def slot_line(a):
    return a.rt.eval(SLOT)("admin")


# --- offline windows -------------------------------------------------------------------------------------------------

def _offline(a, age):
    a.h.online()                                     # no player online: the minute event drains nobody
    return None


def _online(a, age):
    a.h.online(a.p)
    return None


@pytest.fixture(scope="module")
def offline_run():
    acts = {0: lambda a, age: a.slots.__setitem__(0, slot_line(a)), 40: _offline, 129: _online}
    return mini_live(160, acts)


def test_offline_minutes_are_marked_and_not_drained(offline_run):
    slots, rows, paths, events, _ = offline_run
    off = [r["s"] for r in rows if r.get("on") is False]
    assert off == list(range(42, 131))              # rows 42..130 are taken while the player is away
    out, be = RL.replay_live(rows, events, slots[0], ring_paths=paths, sleep_allowed=True)
    # the offline minutes still fire, with the user away, as live: the mod's own minute count agrees
    assert be.NR.server.players.minutes == len(out) == len(rows) - 1
    marked = [r["s"] for r in out if r.get("offline")]
    # replay row k (labelled s_{k+1}) is offline when ring row k or k+1 is: 42..131
    assert marked == list(range(42, 132))
    d = RL.diff(out, rows)
    assert d["classes"]["offline"] == len(marked) and d["offline"] == marked
    for r in out:
        if r.get("offline") and r["s"] - 1 in off:
            assert r["on"] is False                  # no drain ran for that row
    # the reconnect drain is the mod's own: the offline span is clamped at 60 game minutes
    rec = next(r for r in out if r.get("gapM") is not None)
    assert rec["gapM"] == pytest.approx(90.0) and rec["clampM"] == RL.OFFLINE_CAP_M == 60


def test_the_replay_matches_the_live_ring_across_the_offline_window(offline_run):
    slots, rows, paths, events, _ = offline_run
    out, _ = RL.replay_live(rows, events, slots[0], ring_paths=paths, sleep_allowed=True)
    d = RL.diff(out, rows, TIGHT)
    assert d["ok"], d["findings"][:3]
    assert d["fields"]["HUNGER"]["n"] > 50 and any(r["s"] > 132 for r in out if not r.get("offline"))
    # stepping the offline rows (no class) is not the live run: it integrates time the mod never saw
    stepped = [dict(r, on=True) for r in rows]
    for r in stepped:
        r.pop("norec", None)
    out2, _ = RL.replay_live(stepped, events, slots[0], ring_paths=paths, sleep_allowed=True)
    late = [r for r in rows if r["s"] > 135]
    assert not RL.diff([r for r in out2 if r["s"] > 135], late, {"satiety.M": ("rel", 1e-9)})["ok"]


def test_an_online_norec_row_is_the_first_sight_and_is_drained(offline_run):
    slots, rows, paths, events, _ = offline_run
    rows2 = [dict(r) for r in rows]
    for r in rows2:
        if r["s"] == 20:
            r["norec"] = True
    out, _ = RL.replay_live(rows2, events, slots[0], ring_paths=paths, sleep_allowed=True)
    # ruling S0-3: an online row with no record yet is the mod's first sight, which drains that minute
    assert [r["s"] for r in out if r.get("offline") and r["s"] < 40] == []
    assert next(r for r in out if r["s"] == 21)["on"] is True


# --- gaps and suspects ----------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def plain_run():
    def eat(a, age):
        ev = {"age": age + 0.3 / 60, "kind": "eat", "food": "TKX.Mixed650"}
        a.apply(ev, ev["age"])
        return ev
    acts = {0: lambda a, age: a.slots.__setitem__(0, slot_line(a)), 30: eat}
    gaps = [1] * 80
    gaps[50] = 3                                      # a long minute: dtM 3
    return mini_live(80, acts, gaps)


def test_a_long_minute_is_a_gap_and_stepped_by_the_real_age_delta(plain_run):
    slots, rows, paths, events, _ = plain_run
    out, _ = RL.replay_live(rows, events, slots[0], ring_paths=paths, sleep_allowed=True)
    gaps = [r["s"] for r in out if r.get("gap")]
    assert gaps == [51]                               # ring row 51 carries dtM 3
    g = next(r for r in out if r["s"] == 51)
    assert g["dtM"] == pytest.approx(3.0)
    d = RL.diff(out, rows, TIGHT)
    assert d["ok"] and d["classes"]["gap"] == 1 and d["gap"] == [51], d
    by_s = {r["s"]: r for r in rows}
    assert all(r["age"] == by_s[r["s"]]["age"] for r in out if r["s"] in by_s)


def test_a_missing_row_is_a_gap_and_the_next_row_still_compares(plain_run):
    slots, rows, paths, events, _ = plain_run
    cut = [r for r in rows if r["s"] != 60]           # row 60 lost (a page overwritten): s jumps 59 -> 61
    out, _ = RL.replay_live(cut, events, slots[0], ring_paths=paths, sleep_allowed=True)
    assert [r["s"] for r in out if r.get("gap")] == [51, 61]
    assert 61 in [r["s"] for r in out]
    d = RL.diff(out, cut, {"HUNGER": ("abs", 0.002), "satiety.M": ("rel", 0.005)})
    assert d["classes"]["gap"] == 2 and d["gap"] == [51, 61], d
    # the lost drain shows at the gap row only, graded and marked; the rows after it converge
    assert d["findings"] and all(f.get("gap") and f["s"] == 61 for f in d["findings"]), d["findings"]


def test_a_missed_sample_is_a_gap(plain_run):
    slots, rows, paths, events, _ = plain_run
    miss = []
    for r in rows:                                    # the sample of minute 65 raised: no row, ev jumps 64 -> 66
        if r["s"] == 65:
            continue
        r2 = dict(r)
        if r["s"] > 65:
            r2["s"] -= 1
        miss.append(r2)
    out, _ = RL.replay_live(miss, events, slots[0], ring_paths=paths, sleep_allowed=True)
    assert [r["s"] for r in out if r.get("gap")] == [51, 65]
    assert RL.diff(out, miss)["classes"]["gap"] == 2


def test_a_row_whose_drain_did_not_advance_is_suspect_and_not_graded(plain_run):
    slots, rows, paths, events, _ = plain_run
    sus = [dict(r) for r in rows]
    by_s = {r["s"]: r for r in sus}
    by_s[70]["drained"] = by_s[69]["drained"]         # the drain begun after row 69 had not started by row 70
    by_s[70]["HUNGER"] = by_s[70]["HUNGER"] + 0.5     # and the row reads mid-drain
    out, _ = RL.replay_live(sus, events, slots[0], ring_paths=paths, sleep_allowed=True)
    assert [r["s"] for r in out if r.get("suspect")] == [70]
    d = RL.diff(out, sus, TIGHT)
    assert d["ok"] and d["suspect"] == [70] and d["classes"]["suspect"] == 1, d


# --- the start record's read age ------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def read_after_eat():
    """An eat after drain 9, then the slot read, then the ring goes on: the record holds the eat."""
    def eat_then_read(a, age):
        ev = {"age": age + 0.2 / 60, "kind": "eat", "food": "TKX.Mixed650"}
        a.apply(ev, ev["age"])
        a.slots["read"] = slot_line(a)
        a.slots["readAge"] = age + 0.4 / 60
        return ev
    return mini_live(60, {9: eat_then_read})


def test_an_eat_between_the_drain_and_the_read_is_dropped_by_the_read_age(read_after_eat):
    slots, rows, paths, events, _ = read_after_eat
    sa = json.loads(slots["read"])["rec"]["satiety"]["t"]
    assert sa < events[0]["age"] < slots["readAge"]
    out, be = RL.replay_live(rows, events, slots["read"], ring_paths=paths, start_read_age=slots["readAge"], sleep_allowed=True)
    assert be.dropped == events and be.eats == []
    assert RL.diff(out, rows, TIGHT)["ok"]
    # without the read age the eat lands twice: once in the record, once replayed
    out2, be2 = RL.replay_live(rows, events, slots["read"], ring_paths=paths, sleep_allowed=True)
    assert len(be2.eats) == 1
    assert not RL.diff(out2, rows, TIGHT)["ok"]
    # a start record may carry its read age
    carried = dict(json.loads(slots["read"]), readAge=slots["readAge"])
    out3, be3 = RL.replay_live(rows, events, carried, ring_paths=paths, sleep_allowed=True)
    assert be3.dropped == events and [r["HUNGER"] for r in out3] == [r["HUNGER"] for r in out]


def test_a_read_age_before_the_record_or_an_ambiguous_s_keyed_event_raises(read_after_eat):
    slots, rows, paths, events, _ = read_after_eat
    sa = json.loads(slots["read"])["rec"]["satiety"]["t"]
    with pytest.raises(ValueError):
        RL.replay_live(rows, events, slots["read"], ring_paths=paths, start_read_age=sa - 1.0, sleep_allowed=True)
    first = next(r["s"] for r in rows if r["age"] > sa + 1e-9)
    with pytest.raises(ValueError):
        RL.replay_live(rows, [{"s": first, "kind": "eat", "food": "TKX.Mixed650"}], slots["read"], ring_paths=paths,
                       start_read_age=slots["readAge"], sleep_allowed=True)


# --- the event fraction contract ------------------------------------------------------------------------------------

def test_an_eats_kcal_comes_from_the_item_and_its_fraction_never_from_m():
    kcal = []
    for m0 in (0.0, 10.0, 900.0):
        rp = RL.ServerReplay(start={"username": "admin", "firstSeen": 99.0, "lastSeen": 99.0,
                                    "satiety": {"M": m0, "S": 0, "L": 0, "t": 99.0}})
        rp.apply({"kind": "eat", "food": "TKX.Mixed650", "frac": 0.5}, 100.0)
        kcal.append(rp.eats[0]["kcal"])
    assert kcal[0] == kcal[1] == kcal[2] == pytest.approx(325.0)


# --- independence (review mutation M2) ------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ring_live():
    return live_run()


def scaled(rows):
    out = []
    for r in rows:
        r2 = dict(r)
        for f in OUTPUTS:
            if isinstance(r2.get(f), (int, float)) and not isinstance(r2.get(f), bool):
                r2[f] = r2[f] * 1.7 + 0.11
        out.append(r2)
    return out


def test_the_replay_never_reads_the_rings_outputs(ring_live):
    slot, doc, events, _ = ring_live
    rows, paths = RL.load_ring([doc])
    out, _ = RL.replay_live(rows, events, slot, ring_paths=paths, sleep_allowed=True)
    big = scaled(rows)
    assert sum(1 for a, b in zip(rows, big) for f in OUTPUTS if a.get(f) != b.get(f)) > 500
    out2, _ = RL.replay_live(big, events, slot, ring_paths=paths, sleep_allowed=True)
    assert json.dumps(out, sort_keys=True) == json.dumps(out2, sort_keys=True)   # bit-identical
    assert RL.diff(out, rows)["ok"]
    d = RL.diff(out2, big)
    assert not d["ok"] and all(d["fields"][f]["over"] > 0 for f in RL.DEFAULT_TOL), d["fields"]


# --- the stand-in's idle rate (finding F-1) ------------------------------------------------------------------------

def test_an_idle_stand_in_bills_the_default_class():
    rp = RL.ServerReplay(start=None, user="admin")
    K = rp.K
    assert rp.R.u["admin"].rate == K.energy.CLASS_MET.Default == 1.5      # a live idle player reads 1.50 (#2875)
    rp.step(10.0)
    rp.step(10.0 + 1 / 60)
    assert K.energy.classOf(rp.R.u["admin"].rate) == "Default"
    assert rp.record().body.met == K.energy.COMPENDIUM.Default == 1.3     # billed as standing quietly, not DrivingCar
