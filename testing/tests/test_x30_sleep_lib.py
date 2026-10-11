"""x30_sleep_lib (Plan 11f Task 7): the sleep chain's calendar, the replay's sleep events read off the ring's
acute.sleptH (change 4), the window closes against the kernel's own booking, and the night's hold loop (change 3): it
stops at its booked target and always cancels the hold, a budget stop included. Pure Python and the lupa host: no
game."""
import os
import sys
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                          # testing/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x30_sleep_lib as L   # noqa: E402
from pzt.session import Timeline   # noqa: E402

RL = L.RL
START = 4.2                     # the fresh record's first sight on the default fixture (about 11:12 on day 0)
PATHS = ("acute.sleptH", "acute.winSleptH", "acute.winStartH", "acute.debtH", "body.met")


def minute(age):
    return int(round((age - START) * 60))


def arm_events():
    """Four nights at the calendar's ages with their booked targets, as minute events of a synthetic clock."""
    ev = []
    for label, d, h, target, _role in L.NIGHTS:
        a0 = L.at(d, h)
        ev.append({"minute": minute(a0), "kind": "sleep", "asleep": True})
        ev.append({"minute": minute(a0) + int(round(target * 60)), "kind": "sleep", "asleep": False})
    return ev


def arm(events, minutes):
    rows, _ = RL.replay_arm(events, minutes=minutes, start_age=START, dtM=1, backend="server", paths=PATHS,
                            player={"weight": 80.0, "female": False}, hour_offset=7.0, sleep_allowed=True)
    return rows


def ring_of(rows):
    """Arm rows as ring rows: ring row s reads the state drain s-1 left (arm row k is the state after step k, s k+1),
    with a ring row 0 before the first drain."""
    first = {"s": 0, "age": START, "acute.sleptH": 0, "acute.winSleptH": 0,
             "acute.winStartH": rows[0]["acute.winStartH"], "acute.debtH": 0, "on": True}
    return [first] + [dict(r, s=r["s"]) for r in rows]


def test_the_calendar_and_the_schedule():
    kinds = {}
    for age, kind, label, extra in L.SCHEDULE:
        kinds.setdefault(kind, []).append(label)
    assert kinds["maint"] == ["D0_13", "D0_20"]
    assert kinds["request"][0] == "D1_08" and kinds["request"][-1] == "D4_13" and len(kinds["request"]) == 11
    assert kinds["night"] == ["N0", "N1", "N2", "N3"]
    ages = [x[0] for x in L.SCHEDULE]
    assert ages == sorted(ages)
    nights = {label: (age, extra) for age, kind, label, extra in L.SCHEDULE if kind == "night"}
    assert [nights[n][1]["target_h"] for n in ("N0", "N1", "N2", "N3")] == [7.5, 5.5, 9.5, 7.5]
    # every night lies inside one window of a record created at the boot (about 11:12 day 0): its predicted wake at
    # the planning asleep share falls before the next close
    for n, (age, extra) in nights.items():
        wake = age + extra["target_h"] / L.ASLEEP_FRACTION
        close = START + 24.0 * (int((age - START) // 24.0) + 1)
        assert START + 24.0 * int((age - START) // 24.0) < age and wake < close, (n, age, wake, close)
    assert L.next_meal_age(L.at(2, 20.5)) == L.at(3, 8.0)


def test_the_sleep_events_sit_one_row_before_the_row_that_shows_them():
    rows = [{"s": 1, "age": 1.0, "acute.sleptH": 0}, {"s": 2, "age": 1.02, "acute.sleptH": 0},
            {"s": 3, "age": 1.03, "acute.sleptH": 0.0167}, {"s": 4, "age": 1.05, "acute.sleptH": 0.05},
            {"s": 5, "age": 1.07, "on": False}, {"s": 6, "age": 1.08, "acute.sleptH": 0},
            {"s": 7, "age": 1.1, "acute.sleptH": 0}]
    ev = L.sleep_events(rows)
    assert [(e["s"], e["asleep"]) for e in ev] == [(2, True), (4, False)]


def test_the_ring_sleep_events_round_trip_through_the_replay():
    ev = arm_events()
    n = minute(L.at(4, 13.0))
    rows = arm(ev, n)
    ring = ring_of(rows)
    derived = L.sleep_events(ring)
    want = [(e["minute"], e["asleep"]) for e in sorted(ev, key=lambda e: e["minute"])]
    assert [(e["s"], e["asleep"]) for e in derived] == want
    again = arm([{"minute": e["s"], "kind": "sleep", "asleep": e["asleep"]} for e in derived], n)
    for a, b in zip(rows, again):
        assert a["acute.winSleptH"] == b["acute.winSleptH"] and a["acute.debtH"] == b["acute.debtH"]
        assert a["HUNGER"] == b["HUNGER"]


def test_the_window_closes_book_as_the_kernel_and_the_nights_read_their_debts():
    rows = arm(arm_events(), minute(L.at(4, 13.0)))
    closes = L.window_closes(ring_of(rows))
    assert [round(c["booked_h"], 9) for c in closes] == [7.5, 5.5, 9.5, 7.5]
    assert [round(c["debt_after"], 9) for c in closes] == [0.0, 2.0, 1.0, 1.0]
    assert all(abs(c["kernel_diff"]) < 1e-12 for c in closes)
    asleep = [r for r in rows if r["acute.sleptH"] > 0]
    assert asleep and all(abs(r["body.met"] - 1.0) < 1e-12 for r in asleep)


class FakeServer:
    """The night's server side: each record read while the hold is armed advances the world 0.1 game h, booking 0.085 h
    (the asleep share #2840 reads); after the cancel the player is awake and a read advances 1 game minute."""
    def __init__(self):
        self.age, self.win, self.ws = 14.75, 0.0, 4.2
        self.holding = False
        self.cmds = []

    def answer(self, cmd, args):
        self.cmds.append((cmd, args))
        if cmd == "player.sleep.hold":
            self.holding = not args.endswith(" 0")
            return {"armed": self.holding, "before": False, "after": self.holding}
        if cmd == "player.sleep":
            return {"before": True, "after": False, "held": True}
        if cmd == "time.snapshot":
            return {"worldAge": self.age, "hour": 0, "minutes": 0, "mult": 1}
        if cmd == "lua.read":
            if self.holding:
                self.age += 0.1
                self.win += 0.085
            else:
                self.age += 1.0 / 60
            vals = {"acute.winSleptH": self.win, "acute.winStartH": self.ws, "acute.sleptH": 0.0, "acute.debtH": 0.0,
                    "acute.awakeH": 0.0, "acute.boutH": 0.0, "acute.S": 0.1, "satiety.t": self.age}
            return {"ok": True, "values": {p: vals.get(p) for p in args.split()[1:]}}
        return {}


def night_session(tmp_path, fake, budget_at=None):
    S = object.__new__(L.Session)
    S.out = {"phase_walls": {}, "phase_errors": {}, "notes": [], "phases": {}, "deviations": [], "steps": []}
    S.tl, S.t0, S.cur = Timeline(), time.time(), "X"
    S.path = str(tmp_path / "doc.json")
    S.server, S.clients = None, {}
    S.stops, S.marks, S.speeds = [], [], []
    S.budget_s = 1e9
    calls = {"n": 0}

    def step(name, side, cmd, args="", timeout=30, log=True):
        w = S.wall()
        return {"step": name, "side": side, "cmd": cmd, "args": args, "phase": S.cur, "wall_before": w,
                "wall_after": w + 0.2, "took": 0.2, "ack": fake.answer(cmd, args)}

    def check():
        calls["n"] += 1
        if budget_at is not None and calls["n"] >= budget_at:
            raise L.Budget("wall past the budget")
    S.step = step
    S.check = check
    S.one = lambda tag="one": {}
    return S


def test_the_night_stops_at_its_booked_target_and_cancels_the_hold(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "WAKE_SETTLE_S", 1.0)
    monkeypatch.setattr(L, "POLL_S", 0.0)
    fake = FakeServer()
    S = night_session(tmp_path, fake)
    st = S.night("N0", 14.75, {"target_h": 7.5, "role": "rested"})
    assert st["cancel"]["reason"] == "target"
    assert st["placement"]["inside_one_window"] is True
    assert abs(st["booked_h"] - 7.5) <= 0.085 + 1e-9
    seq = [c for c in fake.cmds if c[0] in ("player.sleep.hold", "player.sleep")]
    assert seq == [("player.sleep.hold", "admin 600"), ("player.sleep.hold", "admin 0"), ("player.sleep", "admin false")]
    assert not S.out["deviations"]


def test_a_budget_stop_mid_night_still_cancels_the_hold(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "WAKE_SETTLE_S", 1.0)
    monkeypatch.setattr(L, "POLL_S", 0.0)
    fake = FakeServer()
    S = night_session(tmp_path, fake, budget_at=3)
    with pytest.raises(L.Budget):
        S.night("N0", 14.75, {"target_h": 7.5, "role": "rested"})
    seq = [c for c in fake.cmds if c[0] in ("player.sleep.hold", "player.sleep")]
    assert seq[-2:] == [("player.sleep.hold", "admin 0"), ("player.sleep", "admin false")]
    assert S.stops[-1]["cancel"]["reason"] == "budget"
