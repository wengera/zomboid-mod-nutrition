"""Plan 34 Task 3c (ruling P34-I; the trial `x_trial-ladder-20261109-132439`, the fix arm at b1e99cfc on the `agent`
fixture with the model, P31-T, not evidence; its row in `testing/trials/trials.md`): the retreat's rhythm. After 11
kills with no hit three standing zombies stood on the character at 0.5 tiles and the leave fired (decision line 407);
then thirty lines churned: the retreat's band sent the melee (every one in mode `shove`, the meet spent), the drag
guard at `me.attackers` 2 sent its `many` run superseding it, the next line sent the melee again, the back leg almost
never went, nine bites from line 432 and the drag-down at game minute 622. Three switches of `survive.T19_SWITCHES` on
`threat.Threat`:

- RETREAT_REGAIN (the Fight's `retreat_regain`, `fight.Fight._regain_back`, `_regain_arm`, `_regain_busy`): under the
  retreat, with a standing zombie within POINT_BLANK_R, the band presses once (the melee as the ladder sends it; with
  two or more standing within FIGHT_REACH the shove form: the melee in mode `shove`, else `Shove` at the nearest), then
  the back leg goes and holds until the nearest standing zombie is beyond FIGHT_REACH or RETREAT_REGAIN_S have passed
  since it was sent, then the next press; logged `retreat_regain` {phase, near, since}.
- SPENT_LEAVE (the leave's, `group.ThreatGroup._leave_leg`): with the meet spent (the melee's mode `shove`: a hold or a
  shove-and-stomp Fight, `ThreatGroup._spent_meet`) the retreat's upper bound is GROUP_LEAVE_N - 1, so GROUP_LEAVE_N
  standing within GROUP_ENTRY_R take the `run`, logged `group_leave` {leg "run", n, spent true}.
- DRAG_DEFER (`group.ThreatGroup._drag_defers`, `threat.Threat._threat_plan`): while the leave holds with its leg the
  retreat, the drag guard's row sends no run of its own: its one shove stands, then the line falls through to the
  leave's row (the regain's back leg, the guard's shove its press), logged `drag_fight` {.., deferred "retreat"}.
- RUN_HOLD (amendment 1; the trial `x_trial-ladder-20261109-134527`, lines 412 to 449: the leg flicked between the run
  at five and the retreat at four, the character never running clear): once a leave's leg read `run` it stays `run`
  while that leave holds, logged `group_leave` {leg "run", n, held true}.

The fixtures are synthetic, built from the trial's numbers, never a replay; the fake mod."""
import pytest

from agent.base.planner import fight as F
from agent.base.planner import policies as P
from agent.base.planner import survive as S
from agent.base.planner import threat as T

from .fakemod import MELEE_CAPS
from .test_survive import threat_why, tick
from .test_survive_ak import FIVE_NEAR, ME, WEST_V, band, closing, fight4, guard, pair, z, zm
from .test_survive_an import accept


# ================================================================ the switches and the constant
def test_the_switches_and_the_constant():
    """The three switches and amendment 1's RUN_HOLD on `threat.Threat` (and so `survive.Survive`), on by default,
    appended to `survive.T19_SWITCHES`; RETREAT_REGAIN's Fight rule among `fight.FIGHT_RULES`, dropped by its switch
    alone; RETREAT_REGAIN_S 1.5."""
    assert S.T19_SWITCHES[-4:] == ("RETREAT_REGAIN", "SPENT_LEAVE", "DRAG_DEFER", "RUN_HOLD")
    for name in ("RETREAT_REGAIN", "SPENT_LEAVE", "DRAG_DEFER", "RUN_HOLD"):
        assert getattr(T.Threat, name) is True and getattr(S.Survive, name) is True, name
    assert "retreat_regain" in F.FIGHT_RULES
    on = type("On", (), {n: getattr(S.Survive, n) for n in [r.upper() for r in F.FIGHT_RULES]})()
    every = T.Threat._fight_rules(on)
    on.RETREAT_REGAIN = False
    assert T.Threat._fight_rules(on) == every - {"retreat_regain"}
    assert P.RETREAT_REGAIN_S == 1.5


# ================================================================ (a) RETREAT_REGAIN: press, back, hold, press
PILE = ((0.36, 0.0), (0.3, 0.4), (0.97, 0.0))   # east of ME: 0.36, 0.5 and 0.97 tiles (the trial's lines 410 to 423;
#                                                 two within the melee's crowd radius, so the melee goes)
HALF = ((0.5, 0.0), (0.4, 0.5), (1.0, 0.2))     # the next lines: the nearest at 0.5
GAP = ((2.1, 0.0), (2.3, 0.3), (3.0, 0.0))      # the gap regained: the nearest at 2.1, beyond FIGHT_REACH


def at(offs):
    return [zm(i, ME[0] + dx, ME[1] + dy) for i, (dx, dy) in enumerate(offs, 1)]


def frame(r, f, offs):
    r.frame(x=ME[0], y=ME[1], zombies=at(offs))
    f.observe()


def pressed(tmp_path, rule=True, spent=("arms",), offs=PILE, caps=MELEE_CAPS):
    """The retreat (west) with the pile east, the Fight pinned on 1, its `spent` as Survive sets it (the meet spent:
    the melee's mode `shove`), `retreat_regain` as `rule`; its first step."""
    r, f = fight4(tmp_path, at(offs), target=1, caps=caps)
    f.spent = spent
    if not rule:
        f.rules = f.rules - {"retreat_regain"}
    return r, f, f.step()


def progress(r, a, step):
    r.fake.act(a.aid, "progress", a.type, result={"step": step})
    r.pump()


def test_the_point_blank_press_is_logged_and_its_press_in_flight_holds(tmp_path):
    """The first line: 1 at 0.36 within POINT_BLANK_R: the press is the melee (mode `shove`, the meet spent), logged
    `retreat_regain` {phase "press", near 0.36, since None}; while its press is in flight (`shove`) it holds."""
    r, f, a = pressed(tmp_path)
    assert (a.type, a.args["targetId"], a.args["mode"]) == ("melee", 1, "shove")
    assert f.why["retreat_regain"] == {"phase": "press", "near": pytest.approx(0.36), "since": None}
    accept(r, a, "shove")
    frame(r, f, HALF)
    assert f.busy() is True and f.step() is None


def test_after_the_press_the_back_leg_goes_and_holds_until_regain_s(tmp_path):
    """The trial's lines 410 to 423 under the rule: the press resolved (its step back to `face`), the nearest at 0.5:
    `busy` False and the back leg on the retreat heading in the melee's place, logged `retreat_regain` {phase "back",
    near 0.5}; 0.8 s on, the nearest still at 0.5, it holds (no melee); at 1.6 s the melee again (`retreat_regain`
    {phase "press", since 1.6})."""
    r, f, a = pressed(tmp_path)
    accept(r, a, "shove")
    progress(r, a, "face")
    frame(r, f, HALF)
    assert f.busy() is False
    b = f.step()
    assert b.type == "aim" and f.why["leg"] == "back" and (b.args["vx"], b.args["vy"]) == pytest.approx(WEST_V)
    g = f.why["retreat_regain"]
    assert g["phase"] == "back" and g["near"] == pytest.approx(0.5) and g["since"] == pytest.approx(0.0)
    accept(r, b)
    r.advance(0.8)
    frame(r, f, HALF)
    assert f.busy() is True and f.step() is None
    r.advance(0.8)
    frame(r, f, HALF)
    assert f.busy() is False
    c = f.step()
    assert (c.type, c.args["mode"]) == ("melee", "shove")
    assert f.why["retreat_regain"]["phase"] == "press" and f.why["retreat_regain"]["since"] == pytest.approx(1.6)


def test_a_press_that_ended_takes_the_back_leg_too(tmp_path):
    """The trial's own shape: the shove-mode melee ended (superseded) with the nearest at 0.5: the back leg, no melee."""
    r, f, a = pressed(tmp_path)
    accept(r, a)
    r.fake.act(a.aid, "failed", "melee", reason="superseded")
    r.pump()
    frame(r, f, HALF)
    b = f.step()
    assert b.type == "aim" and f.why["leg"] == "back" and f.why["retreat_regain"]["phase"] == "back"


def test_the_gap_regained_ends_the_hold_and_the_band_s_melee_goes(tmp_path):
    """The back leg sent, 0.6 s on the nearest at 2.1 (beyond FIGHT_REACH): `busy` False and the melee again (the
    band's, at the stance's back leg within KEEP_R), no press logged (none within POINT_BLANK_R)."""
    r, f, a = pressed(tmp_path)
    accept(r, a, "shove")
    progress(r, a, "face")
    frame(r, f, HALF)
    b = f.step()
    accept(r, b)
    r.advance(0.6)
    frame(r, f, GAP)
    assert f.busy() is False
    c = f.step()
    assert (c.type, c.args["targetId"]) == ("melee", 1) and "retreat_regain" not in f.why


def test_with_retreat_regain_off_the_melee_holds_and_goes_again_every_line(tmp_path):
    """A pin (`retreat_regain` off, the rule before it): the resolved press does not give way, and the melee ended
    (superseded) is sent again on the next line, no back leg, no `retreat_regain`."""
    r, f, a = pressed(tmp_path, rule=False)
    assert "retreat_regain" not in f.why
    accept(r, a, "shove")
    progress(r, a, "face")
    frame(r, f, HALF)
    assert f.busy() is True and f.step() is None
    r.fake.act(a.aid, "failed", "melee", reason="superseded")
    r.pump()
    frame(r, f, HALF)
    c = f.step()
    assert c.type == "melee" and "retreat_regain" not in f.why


# ================================================================ (b) the press's form
TWO_IN = ((0.6, 0.0), (1.5, 0.3), (3.0, 0.5))    # two standing within FIGHT_REACH
ONE_IN = ((0.6, 0.0), (3.0, 0.5), (3.5, -0.5))   # one


@pytest.mark.parametrize("offs, rule, mode", [(TWO_IN, True, "shove"), (ONE_IN, True, "strike"),
                                              (TWO_IN, False, "strike")])
def test_two_in_reach_make_the_press_the_shove(tmp_path, offs, rule, mode):
    """Unspent: with two standing within FIGHT_REACH the press is the melee in mode `shove` (the knockback opens room);
    with one it is the strike; with the rule off (a pin) the strike."""
    r, f, a = pressed(tmp_path, rule=rule, spent=(), offs=offs)
    assert (a.type, a.args["targetId"], a.args["mode"]) == ("melee", 1, mode)


def test_without_the_melee_two_in_reach_make_the_press_a_shove_at_the_nearest(tmp_path):
    """A build announcing no `melee` (the fake mod's PZA/1.7 hello): the press with two in reach is `Shove` at 1."""
    r, f, a = pressed(tmp_path, spent=(), offs=TWO_IN, caps=None)
    assert (a.type, a.args["targetId"]) == ("shove", 1) and f.why["retreat_regain"]["phase"] == "press"


# ================================================================ (c) SPENT_LEAVE
def test_a_spent_meet_takes_the_run_at_group_leave_n(tmp_path):
    """Three standing closing within GROUP_ENTRY_R with the meet spent (the tired hold, `stats.fatigue` 0.7): the leg is
    the `run` (`group_leave` {leg "run", n 3, spent true}, the threat plan's `many` flee, a run steer); unspent, the
    retreat; with SPENT_LEAVE off and spent (a pin), the retreat."""
    r, sv = closing(tmp_path, fatigue=0.7)
    why = threat_why(tmp_path)
    assert why["group_leave"]["leg"] == "run" and why["group_leave"]["n"] == 3 and why["group_leave"]["spent"] is True
    assert why["flee"] == "many" and r.cmd()[0] == "steer" and r.cmd()[1]["gait"] == "run"
    (tmp_path / "fresh").mkdir()
    closing(tmp_path / "fresh")
    gl = threat_why(tmp_path / "fresh")["group_leave"]
    assert gl["leg"] == "retreat" and "spent" not in gl
    (tmp_path / "off").mkdir()
    closing(tmp_path / "off", off=("SPENT_LEAVE",), fatigue=0.7)
    gl = threat_why(tmp_path / "off")["group_leave"]
    assert gl["leg"] == "retreat" and "spent" not in gl


# ================================================================ (d) DRAG_DEFER
SHOVE_FIRST = ((100.0, 200.7), (97.65, 199.95), (100.5, 206.3))   # 1 at 0.54: the leave's shove on its first line
TWO_MORE = ((102.3, 200.5), (100.5, 202.8))                        # 1.8 and 2.3 tiles: five standing, the `run`


def deferred(tmp_path, extra=(), off=()):
    """The leave opened with its one shove (GROUP_LEAVE and DRAG_GUARD_FIGHT on), that shove done; then two guard
    lines on the drag pile (`me.attackers` 2 under a hit reaction), `extra` standing beside it, each line's new command
    answered done. Each guard line's (command or None, threat why)."""
    r, sv = closing(tmp_path, on=("GROUP_LEAVE", "DRAG_GUARD_FIGHT"), second=SHOVE_FIRST, off=off)
    assert threat_why(tmp_path)["group_leave"]["leg"] == "shove" and r.cmd() == ("shove", {"targetId": 1})
    r.answer("done")
    zs = guard(())["zombies"] + [z(4 + i, x, y) for i, (x, y) in enumerate(extra)]
    out = []
    for _ in range(2):
        n = len(r.acts.history)
        r.advance(0.5)
        r.frame(x=100.5, y=200.5, zombies=zs, attackers=2, hit_reaction="Bite")
        tick(r, sv)
        sent = len(r.acts.history) > n
        out.append((r.cmd() if sent else None, threat_why(tmp_path)))
        if sent:
            r.answer("done")
    return r, sv, out


def test_under_the_retreat_the_guard_shoves_once_then_the_retreat_s_back_leg(tmp_path):
    """The leave's retreat held under the drag pile: the guard's one shove (as before), then on the spent line no run:
    the Fight's back leg on the retreat heading (the regain's, the guard's shove its press), logged `drag_fight`
    {spent 1, why "hit", deferred "retreat"} and `retreat_regain` {phase "back"}."""
    r, sv, out = deferred(tmp_path)
    (cmd0, why0), (cmd1, why1) = out
    assert cmd0 == ("shove", {"targetId": 1}) and why0["drag_fight"]["target"] == 1 and why0["group"] == "drag"
    assert why1["drag_fight"] == {"spent": 1, "why": "hit", "deferred": "retreat"}
    assert why1["fight"] is True and why1["group_leave"]["leg"] == "retreat" and "group" not in why1
    assert cmd1[0] == "aim" and why1["retreat_regain"]["phase"] == "back"
    assert sv.mode == "fight"


def test_under_the_run_leg_the_guard_s_run_as_before(tmp_path):
    """Five standing (above RETREAT_MAX_N, the leg the `run`): the guard's shove, then its run steer as before."""
    r, sv, out = deferred(tmp_path, extra=TWO_MORE)
    (cmd0, _), (cmd1, why1) = out
    assert cmd0 == ("shove", {"targetId": 1})
    assert cmd1[0] == "steer" and cmd1[1]["gait"] == "run" and why1["drag_fight"] == {"spent": 1, "why": "hit"}


def test_with_drag_defer_off_the_guard_runs(tmp_path):
    """A pin (DRAG_DEFER off, the rule before it): the guard's shove, then its run steer under the leave's retreat."""
    r, sv, out = deferred(tmp_path, off=("DRAG_DEFER",))
    (cmd0, _), (cmd1, why1) = out
    assert cmd0 == ("shove", {"targetId": 1})
    assert cmd1[0] == "steer" and cmd1[1]["gait"] == "run" and why1["drag_fight"] == {"spent": 1, "why": "hit"}


# ================================================================ amendment 1: RUN_HOLD
FAR = ((100.5, 207.5), (93.0, 200.5), (108.5, 200.5), (100.5, 193.0))   # 7.0 to 8.0 tiles: beyond GROUP_ENTRY_R


def counted(n):
    """FIVE_NEAR's first `n` within GROUP_ENTRY_R, the rest moved beyond it."""
    return FIVE_NEAR[:n] + FAR[:5 - n]


def held_run(tmp_path, hold=True):
    """The leave opened by five closing (the `run`), then the counts 4, 4, 3, 2, 2, 2 a line, RUN_HOLD `hold`; each
    line's `group_leave`, the first line's included."""
    r, sv = band(tmp_path, 5)
    sv.RUN_HOLD = hold
    out = [threat_why(tmp_path)["group_leave"]]
    for n in (4, 4, 3, 2, 2, 2):
        r.advance(0.5)
        r.frame(x=100.5, y=200.5, zombies=pair(counted(n)))
        tick(r, sv)
        out.append(threat_why(tmp_path)["group_leave"])
    return sv, out


def test_a_leave_that_ran_keeps_the_run_until_it_ends_strung(tmp_path):
    """The counts 5, 4, 4, 3, 2, 2, 2: the leg reads `run` on the first four lines (held from the second, `held` true,
    `n` the count) and on the two lines STRUNG_HOLD holds at two; the seventh ends the leave `strung`."""
    sv, gl = held_run(tmp_path)
    assert [g.get("leg") for g in gl[:6]] == ["run"] * 6
    assert [g.get("held", False) for g in gl[:4]] == [False, True, True, True]
    assert [g["n"] for g in gl[:4]] == [5, 4, 4, 3]
    assert gl[6] == {"end": "strung", "n": 2} and sv.leave is None


def test_with_run_hold_off_the_count_reads_the_retreat_again(tmp_path):
    """A pin (RUN_HOLD off, the rule before it): the second and third lines (four standing) read the retreat."""
    sv, gl = held_run(tmp_path, hold=False)
    assert gl[0]["leg"] == "run" and gl[1]["leg"] == "retreat" and gl[2]["leg"] == "retreat"
    assert all("held" not in g for g in gl)
