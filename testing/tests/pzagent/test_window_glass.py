"""The planner's climb gate on the window's glass (Plan 32 Task 6, the spec `2026-11-08-plan-32-the-facing-design.md`
section 4.5; Angus's direction of 2026-11-08, memory `window-broken-glass`): the jar rows T101.1-T101.3 on
docs/platform/agent.md (a climb through a smashed window whose glass is in cuts a hand or a forearm 1 time in 2, #4366;
vanilla's ISRemoveBrokenGlass removes it with no glove or held-item test) and the map's PZA/1.11 windowPortal `glass`.

- `windows.usable_windows` leaves a window whose record reads glass out unless `GLASS_CLEAR` (on), and a `glass` end
  (the Lua's refusal) is a `WINDOW_DEAD` end: the window is left for another way.
- `windows.clear_for` / `window_cmd`: the window command carries `clear` true when `GLASS_CLEAR` and the record reads
  glass or the command smashes (the act's own smash leaves the glass in); the senders (`goal_policies`' window route,
  the Flee's window way out) build their command through `window_cmd`.
- `door_held`: a window between the player and a zombie stays a `leave`, its why carrying `glass` true when the window
  reads glass.
- F17's replay (`testing/artifacts/f_goals_17-20261108-172833/`): the `health` flee's window climb a207 (decision line
  805, `Window(10738, 10632, smash=True)`) went through a window the map read shut and locked and the act climbed at
  once (done with `opened` and `smashed` false), so the window was destroyed (#4366's canClimbThrough), its glass
  unread on PZA/1.10; with the glass read in, the command carries `clear` true, and with `GLASS_CLEAR` off the window
  is no way out."""
import os
import types

import pytest

from agent.base.planner import goals as GL
from agent.base.planner import night
from agent.base.planner import windows as WN
from agent.base.pza1 import Window
from agent.base.replay_decisions import read_record
from agent.base.world import World

from .test_policies import Rig, square, zombie
from .test_survive import threat_why, tick


ART = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "artifacts",
                   "f_goals_17-20261108-172833")
WIN = {"open": False, "locked": False, "barricaded": False}
GLASS = dict(WIN, smashed=True, glass=True)
CLEARED = dict(WIN, smashed=True, glass=False)


def win_ground(rec, n=1):
    """Building 1's room squares x 0..4, its window edge on x 5's west side at y 0..n-1 holding `rec`, open ground east."""
    out = []
    for x in range(0, 9):
        for y in range(0, 3):
            if x <= 4:
                out.append(square(x, y, room="kitchen", building=1))
            elif x == 5:
                out.append(square(x, y, blockW=True, edgeW=True, window=rec if y < n else None))
            else:
                out.append(square(x, y))
    return out


def rig(tmp_path, rec):
    r = Rig(tmp_path)
    r.scan(win_ground(rec))
    r.frame(x=2.5, y=0.5)
    return r


def test_the_switch_and_the_glass_end():
    assert WN.GLASS_CLEAR is True and "glass" in WN.WINDOW_DEAD


@pytest.mark.parametrize("rec, on, kept", [(WIN, True, True), (GLASS, True, True), (GLASS, False, False),
                                           (CLEARED, False, True), (dict(WIN, smashed=None, glass=None), False, True)])
def test_usable_windows_leaves_a_glazed_window_out_only_with_the_clear_off(tmp_path, monkeypatch, rec, on, kept):
    monkeypatch.setattr(WN, "GLASS_CLEAR", on)
    r = rig(tmp_path, rec)
    assert WN.usable_windows(r.world, 1, 0) == ([((5, 0, 0), False)] if kept else [])


def test_a_glass_end_leaves_the_window_out(tmp_path):
    """The Lua's `glass` refusal (no clear sent, or the removal's class absent on an older build) leaves the window out
    for DOOR_RETRY_MIN game minutes like any WINDOW_DEAD end."""
    r = rig(tmp_path, GLASS)
    a = types.SimpleNamespace(reason="glass", state="rejected", args={"x": 5, "y": 0})
    assert WN.note_window_end(r.world, (5, 0, 0), a) == "glass" and WN.usable_windows(r.world, 1, 0) == []


@pytest.mark.parametrize("rec, smash, on, clear", [(GLASS, False, True, True), (WIN, False, True, False),
                                                   (WIN, True, True, True), (CLEARED, False, True, False),
                                                   (GLASS, True, False, False), (None, False, True, False)])
def test_clear_for_and_window_cmd(tmp_path, monkeypatch, rec, smash, on, clear):
    monkeypatch.setattr(WN, "GLASS_CLEAR", on)
    r = rig(tmp_path, rec if rec is not None else WIN)
    if rec is None:
        r.world.map[(5, 0, 0)].pop("window")
    assert WN.clear_for(r.world, (5, 0, 0), smash) is clear
    cmd = WN.window_cmd(r.world, (5, 0, 0), smash)
    assert cmd == Window(5, 0, smash=smash, clear=clear)
    assert ("clear" in cmd.args()) is clear


def test_window_pick_sends_through_window_cmd_and_a_glazed_window_with_the_clear_off_is_no_pick(tmp_path, monkeypatch):
    r = rig(tmp_path, GLASS)
    r.frame(x=6.5, y=0.5)
    assert GL.window_pick(r.world, 1) == (5, 0, 0, False)
    monkeypatch.setattr(WN, "GLASS_CLEAR", False)
    assert GL.window_pick(r.world, 1) is None


# ---------------------------------------------------------------- door_held: a window between, with its glass
def window_rig(tmp_path, rec):
    from .fakemod import MELEE_CAPS
    from agent.base.planner import survive as S
    from .test_survive_g import Src
    r = Rig(tmp_path, caps=MELEE_CAPS)
    sv = S.Survive(r.world, r.acts, str(tmp_path / "decision.log"), r.clock, source=Src(None))
    out = []
    for x in range(10760, 10779):
        for y in range(10630, 10637):
            if x <= 10769:
                out.append(square(x, y, room="bedroom", building=5))
            elif x == 10770:
                out.append(square(x, y, blockW=True, edgeW=True, window=rec if y == 10633 else None))
            else:
                out.append(square(x, y))
    r.scan(out)
    me = (10773.0, 10633.5)
    r.frame(x=me[0], y=me[1], zombies=[zombie(9, 10769.5, 10633.5, me=me)], health=60.0)
    return r, sv


@pytest.mark.parametrize("rec, glass", [(GLASS, True), (WIN, None), (CLEARED, None)])
def test_a_zombie_behind_a_window_is_left_and_the_why_names_its_glass(tmp_path, rec, glass):
    r, sv = window_rig(tmp_path, rec)
    tick(r, sv)
    w = threat_why(tmp_path)["door_held"]
    assert (w["kind"], w["decision"], w["n_behind"]) == ("window", "leave", 1)
    assert w.get("glass") is glass and ("glass" in w) is (glass is True)


# ---------------------------------------------------------------- F17's window climb a207, replayed
def world_at(line):
    lines, rows = read_record(ART)
    w = World()
    i = 0
    for k, row in enumerate(rows, 1):
        while i < len(lines) and lines[i].get("wallMs", 0) / 1000.0 <= row["wall"]:
            w.apply(lines[i])
            i += 1
        if k == line:
            return w, row, lines
    raise AssertionError(line)


@pytest.fixture(scope="module")
def f17():
    return world_at(805)


SQ = (10738, 10632, 0)


def test_f17_s_window_climb_went_through_a_window_the_map_read_shut_and_the_act_climbed_at_once(f17):
    w, row, lines = f17
    assert row["action"] == {"type": "window", "args": {"smash": True, "x": 10738, "y": 10632}} and row["sent"]
    assert w.map[SQ]["window"] == {"open": False, "locked": True, "barricaded": False}   # 1.10: no glass read
    done = [l for l in lines if l["kind"] == "act" and l["aid"] == "a207" and l["state"] == "done"]
    assert len(done) == 1 and done[0]["result"] == {"cut": False, "opened": False, "smashed": False, "wounds": 0}


def test_f17_with_the_glass_read_in_the_flee_s_window_carries_clear_and_with_the_clear_off_it_is_no_way_out(
        f17, monkeypatch):
    w, _, _ = f17
    rec = w.map[SQ]["window"]
    monkeypatch.setitem(w.map[SQ], "window", dict(rec, smashed=True, glass=True))
    exits = night.window_exits(w, 3, 0)
    e = next(e for e in exits if e["window"] == SQ)
    assert e["smash"] is True
    assert WN.window_cmd(w, e["window"], e["smash"]) == Window(10738, 10632, smash=True, clear=True)
    monkeypatch.setattr(WN, "GLASS_CLEAR", False)
    assert all(e["window"] != SQ for e in night.window_exits(w, 3, 0))
    monkeypatch.setitem(w.map[SQ], "window", rec)
    assert any(e["window"] == SQ for e in night.window_exits(w, 3, 0))   # unread glass: no gate (a PZA/1.10 record)
