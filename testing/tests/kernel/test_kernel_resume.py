"""The resume kernel (NR_Kernel_Resume.lua, Plan 16 Task 2; spec section 1.1): nothing about a character changes
while its player is offline. K.resume.shift moves every world-age stamp a record holds (K.resume.STAMPS) by a gap,
K.resume.resume moves them by the gap from the record's last step age (K.resume.fromH) to the touch's age, and
K.resume.substeps splits an online stall into steps of at most K.resume.STEP_M.

The session `host` fixture loads every NR_Kernel*.lua, so the coverage gate (test_zz_coverage.py) sees each line
here. The server-level freeze (a logout of 3 game days, 30 and 59 minutes, the stall, the eat at the return and the
online record day) is test_offline_freeze.py's.
"""
import math

import pytest

NAN = float("nan")


def R(host):
    return host.K.resume


def lst(t):
    return [t[i] for i in range(1, len(t) + 1)]


def full_record(host, at=100.0):
    """Every stamp of K.resume.STAMPS at `at`, beside fields the resume never touches."""
    return host.table({
        "username": "u", "firstSeen": 3.0, "lastSeen": at, "kineticsAge": at,
        "satiety": {"t": at, "nicH": at - 30.0, "M": 400.0, "S": 0.25},
        "nutrients": {"lastAgeH": at, "lastDayIndex": 4},
        "body": {"lastAgeH": at, "dayStartH": 96.0, "bornAge": 3.0, "dayIndex": 4, "trail": {"at": at}},
        "acute": {"winStartH": 98.0, "mass90ageH": 50.0, "lastFedAgeH": 99.5, "lastVigAgeH": -1e9, "caf": 80.0},
        "drain": {"fedAgeH": 97.25, "acuteH": 0.0},
        "monotony": {"t": {"Base.Bread": {"n": 2.0, "last": 99.0}, "Base.Apple": {"n": 1.0, "last": 80.0}}},
    })


def test_the_stamp_list_names_every_world_age_clock(host):
    stamps = lst(R(host).STAMPS)
    assert stamps == ["lastSeen", "kineticsAge", "satiety.t", "satiety.nicH", "nutrients.lastAgeH", "body.lastAgeH",
                      "body.dayStartH", "acute.winStartH", "acute.mass90ageH", "acute.lastFedAgeH",
                      "acute.lastVigAgeH", "drain.fedAgeH", "monotony.t.*.last"]
    assert len(lst(R(host).SEGS)) == len(stamps)
    assert lst(R(host).SEGS[13]) == ["monotony", "t", "*", "last"]
    assert lst(R(host).split("lastSeen")) == ["lastSeen"]
    kept = host.py(R(host).KEPT)
    assert sorted(kept) == ["body.bornAge", "body.trail.at", "body.trail.ch", "firstSeen"]
    assert not set(kept) & set(stamps)
    assert R(host).STEP_M == 60 and R(host).SLOT_SUBSTEPS == 4 and R(host).MAX_SUBSTEPS is None


def test_from_h_is_the_latest_finite_step_stamp(host):
    r = full_record(host)
    assert R(host).fromH(r) == 100.0
    r.satiety.t = 100.5                                     # the writer stepped last
    assert R(host).fromH(r) == 100.5
    r.lastSeen = NAN                                        # a stamp that is not finite is ignored
    r.kineticsAge = None
    r.nutrients = "corrupt"                                 # a sub-table that is not a table reads none
    r.body = None
    assert R(host).fromH(r) == 100.5
    assert R(host).fromH(host.table({"username": "u"})) is None
    assert R(host).later(None, 5.0) == 5.0 and R(host).later(7.0, 5.0) == 7.0 and R(host).later(7.0, NAN) == 7.0
    assert R(host).field(3, "t") is None and R(host).field(host.table({"t": 2.0}), "t") == 2.0


def test_shift_moves_every_stamp_and_nothing_else(host):
    # the successor of Plan 12's K.acute.skip and skipRecord tests: every acute anchor, every monotony stamp, the
    # nicotine anchor, the unfed clock, the step stamps and the record day move by the gap; nothing else moves
    r = full_record(host)
    before = host.py(r)
    R(host).shift(r, 72.0)
    after = host.py(r)
    assert after["lastSeen"] == after["kineticsAge"] == 172.0
    assert after["satiety"]["t"] == 172.0 and after["satiety"]["nicH"] == 142.0
    assert after["nutrients"]["lastAgeH"] == after["body"]["lastAgeH"] == 172.0
    assert after["body"]["dayStartH"] == 168.0
    assert (after["acute"]["winStartH"], after["acute"]["mass90ageH"], after["acute"]["lastFedAgeH"]) == (170.0, 122.0, 171.5)
    assert after["acute"]["lastVigAgeH"] == -1e9 + 72.0
    assert after["drain"]["fedAgeH"] == 169.25
    assert after["monotony"]["t"]["Base.Bread"]["last"] == 171.0 and after["monotony"]["t"]["Base.Apple"]["last"] == 152.0
    for k in ("firstSeen", "username"):                     # identity: kept
        assert after[k] == before[k]
    assert after["body"]["bornAge"] == 3.0 and after["body"]["trail"]["at"] == 100.0 and after["body"]["dayIndex"] == 4
    assert after["satiety"]["M"] == 400.0 and after["acute"]["caf"] == 80.0 and after["monotony"]["t"]["Base.Bread"]["n"] == 2.0


def test_shift_leaves_absent_or_unreadable_tables_and_stamps(host):
    # the successor of test_skip_record_leaves_absent_or_unreadable_monotony_and_nicotine: a sub-table that is absent
    # or not a table, an entry that is not one, and a stamp that is not finite are left for their owners' heals
    r = host.table({"lastSeen": 10.0, "satiety": "y", "monotony": {"t": {"Base.Odd": "corrupt", "Base.X": {"last": NAN}}},
                    "acute": {"winStartH": None, "mass90ageH": 5.0}})
    R(host).shift(r, 5.0)
    assert r.lastSeen == 15.0 and r.satiety == "y" and r.monotony.t["Base.Odd"] == "corrupt"
    assert math.isnan(r.monotony.t["Base.X"].last) and r.acute.winStartH is None and r.acute.mass90ageH == 10.0
    r2 = host.table({"monotony": {"t": 3}})
    R(host).shift(r2, 5.0)
    assert r2.monotony.t == 3


def test_a_stamp_at_the_last_step_lands_on_the_touch_exactly(host):
    # Plan 12 B2 F1's successor: a stamp laid at the departure minute lands on the return's age with no rounding, so
    # the first step back integrates exactly 0 (16.166666666666668 + (50.4 - 16.166666666666668) is 50.400000000000006,
    # not 50.4: the gap does not round-trip, fix 1 F5)
    last, back = 16.166666666666668, 50.4
    assert last + (back - last) != back
    r = full_record(host, last)
    gap = R(host).resume(r, back)
    assert gap == back - last
    assert r.lastSeen == r.kineticsAge == r.satiety.t == r.nutrients.lastAgeH == r.body.lastAgeH == back
    assert R(host).moved(last, gap, last, back) == back
    assert R(host).moved(50.0, 10.0, None, None) == 60.0 and math.isnan(R(host).moved(NAN, 10.0, last, back))


def test_resume_moves_nothing_without_a_gap_a_clock_or_a_step(host):
    r = full_record(host)
    assert R(host).resume(r, NAN) == 0 and R(host).resume(r, None) == 0
    assert R(host).resume(r, 100.0) == 0 and R(host).resume(r, 99.0) == 0   # a world behind the record: the backup's case
    assert R(host).resume(host.table({"username": "u"}), 500.0) == 0
    assert host.py(r) == host.py(full_record(host))
    assert R(host).resume(r, 172.0) == 72.0 and r.body.dayStartH == 168.0


@pytest.mark.parametrize("span_m,want", [
    (0.0, 1), (60.0, 1),                                    # at the bound: one step
    (60.9375, 2), (180.0, 3),                               # past it: the fewest equal sub-steps of at most 60
    (30 * 60.0, 30),                                        # no cap here: the players' slot runs SLOT_SUBSTEPS of them
    (-30.0, 1),                                             # a world behind: one step (the adapters clamp it at 0)
])
def test_substeps_split_an_online_stall(host, span_m, want):
    # the successor of test_the_gap_threshold_is_k_body_gap_m: the ages are exact in binary, so the 60.9375-minute
    # span kills a `> 61` mutant and the 60-minute one a `> 59`
    assert R(host).substeps(100.0, 100.0 + span_m / 60) == want


def test_substeps_of_an_unread_age_is_one_step(host):
    assert R(host).substeps(None, 5.0) == 1 and R(host).substeps(5.0, NAN) == 1
