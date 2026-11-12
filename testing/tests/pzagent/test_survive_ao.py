"""Plan 34 Task 3b (ruling P34-G; the trial `x_trial-ladder-20261109-123231`, the fix arm on the `agent` fixture with
the model, P31-T, not evidence; its row in `testing/trials/trials.md`): LEAVE_ENTRY, a switch of
`survive.T19_SWITCHES` on `threat.Threat`, the leave's entry (`group.ThreatGroup._leave_entry`).

- No cover exemption: at decision line 12 three standing zombies (8932, 8933, 8927) closed within 6 tiles with a wall
  at the character's back (`group_leave` {withheld "cover", cover {at [10718, 10193, "W"], kind "wall"}}) and the leave
  never fired; the character fought the trio with its back to the wall. A wall at the back stops no drag-down (#4290),
  so under the rule the back read is logged beside the entry (`group_leave` {closing, cover}) and the leave enters
  (Plan 35: the retreat's heading is the reflex's withdraw bias, its footwork vetoing a step into a wall).
- The leave with the group on the character: from line 25 to 60 the pair rule fought three standing zombies at 0.4 to
  0.9 tiles with no leave line, since the closing read needs each of the three nearer than on the line before and
  zombies already at the character jitter rather than close. Under the rule GROUP_LEAVE_N or more standing within
  GROUP_ENTRY_R with the nearest within KEEP_R enter the leave, closing or not, logged `group_leave` {on, near}.

The fixtures are synthetic, the fake mod."""
import pytest

from agent.base.planner import survive as S
from agent.base.planner import threat as T

from .test_policies import square
from .test_survive import make, threat_why, tick
from .test_survive_ak import ME, T17, closing, pair

WALL = [square(101, 200, blockW=True)]   # the W edge of square (101, 200): 0.5 tiles east, behind the player as the
#                                          trio closes from the west (the trial's line 12: a wall edge at the back)


def test_the_switch():
    """LEAVE_ENTRY on `threat.Threat`, on by default, the last of `survive.T19_SWITCHES` (Plan 35 Task 8 deleted
    CRAWLER_CLEAR, which it followed, and RETREAT_REGAIN; Plan 37 Task 3 SPENT_LEAVE and RUN_HOLD, which followed
    it)."""
    t19 = S.T19_SWITCHES
    assert t19[-1] == "LEAVE_ENTRY"
    assert T.Threat.LEAVE_ENTRY is True and S.Survive.LEAVE_ENTRY is True


# ================================================================ (a) no cover exemption
def test_a_closing_trio_with_a_wall_at_the_back_enters_the_leave(tmp_path):
    """The trial's line 12: three closing within GROUP_ENTRY_R, a wall edge 0.5 tiles behind (within WALL_R): the rule
    on enters the leave, its why carrying the back read (`group_leave` {closing, cover, leg "retreat"}: the nearest at
    2.90 tiles, beyond STAND_MIN_R), the Fight's retreat, no steer."""
    r, sv = closing(tmp_path, scan=WALL)
    why = threat_why(tmp_path)
    gl = why["group_leave"]
    assert "withheld" not in gl and sv.leave is not None and sv.mode == "fight"
    assert gl["closing"] == [2, 1, 3] and gl["cover"] == {"kind": "wall", "at": [101, 200, "W"]}
    assert gl["leg"] == "retreat" and why["group_retreat"]["leg"] == "retreat" and r.cmd()[0] == "aim"


def test_with_leave_entry_off_the_wall_withholds_the_leave(tmp_path):
    """A pin: with LEAVE_ENTRY off the wall at the back withholds the leave as before (`withheld` "cover")."""
    r, sv = closing(tmp_path, scan=WALL, off=("LEAVE_ENTRY",))
    why = threat_why(tmp_path)
    assert sv.leave is None and why.get("flee") != "leave"
    assert why["group_leave"] == {"withheld": "cover", "closing": [2, 1, 3],
                                  "cover": {"kind": "wall", "at": [101, 200, "W"]}}


# ================================================================ (b), (c) the group already on the character
def still(tmp_path, at, on=True):
    """Two ticks of zombies 1.. standing at `at` (the same squares both lines: none closing on the second),
    GROUP_LEAVE on with the other T18 switches off, LEAVE_ENTRY off on the first line (no leave before the line under
    test) and `on` on the second."""
    r, sv = make(tmp_path)
    for name in T17:
        setattr(sv, name, name == "GROUP_LEAVE")
    for entry in (False, on):
        sv.LEAVE_ENTRY = entry
        r.frame(x=ME[0], y=ME[1], zombies=pair(at))
        tick(r, sv)
        r.advance(0.5)
    return r, sv


ON_ME = ((101.1, 200.5), (100.5, 202.0), (98.5, 200.5))   # 0.6, 1.5 and 2.0 tiles: the trial's lines 25 to 60


def test_three_standing_on_the_character_enter_the_leave_though_none_closes(tmp_path):
    """Three standing within GROUP_ENTRY_R at the same distances on both lines, the nearest at 0.6 (within KEEP_R and
    STAND_MIN_R): the leave enters, logged `group_leave` {on [1, 2, 3], near 0.6}, its leg the retreat (Plan 35 Task 8
    deleted the leave's first-line shove)."""
    r, sv = still(tmp_path, ON_ME)
    why = threat_why(tmp_path)
    gl = why["group_leave"]
    assert sv.leave is not None and "closing" not in gl
    assert gl["on"] == [1, 2, 3] and gl["near"] == pytest.approx(0.6)
    assert gl["leg"] == "retreat" and sv.mode == "fight"


def test_the_leave_on_the_character_retreats_after_its_shove(tmp_path):
    """The line after the `on` entry holds the leave (three within GROUP_ENTRY_R), its leg the retreat."""
    r, sv = still(tmp_path, ON_ME)
    r.frame(x=ME[0], y=ME[1], zombies=pair(ON_ME))
    tick(r, sv)
    why = threat_why(tmp_path)
    assert why["group_leave"]["n"] == 3 and why["group_leave"]["leg"] == "retreat" and sv.mode == "fight"


def test_three_standing_beyond_keep_r_none_closing_make_no_entry(tmp_path):
    """The same with the nearest at 3.0 tiles (beyond KEEP_R): no entry, the closing read alone decides there."""
    still(tmp_path, ((103.5, 200.5), (100.5, 204.0), (96.5, 200.5)))
    why = threat_why(tmp_path)
    assert "group_leave" not in why


def test_two_standing_on_the_character_make_no_entry(tmp_path):
    """Two standing at 0.5 tiles, none closing: no entry (GROUP_LEAVE_N 3; the pair rule's)."""
    r, sv = still(tmp_path, ((101.0, 200.5), (100.0, 200.5)))
    why = threat_why(tmp_path)
    assert sv.leave is None and "group_leave" not in why


def test_with_leave_entry_off_three_on_the_character_make_no_entry(tmp_path):
    """A pin: with LEAVE_ENTRY off the three on the character, none closing, make no entry (the trial's lines 25 to 60
    as they ran)."""
    r, sv = still(tmp_path, ON_ME, on=False)
    why = threat_why(tmp_path)
    assert sv.leave is None and "group_leave" not in why
