"""Plan 34 Task 3 (the column; F19, `f_goals_19-20261109-060929`, GUIDE.md § 4 "The retreat's live reading") and fix B
of ruling P34-A, as Plan 35 Task 8 (the deletion; the reflex owns contact) left them: RETREAT_GAP, RETREAT_MELEE,
STRUNG_HOLD and CRAWLER_CLEAR are deleted with their tests (named in the task report), and what stays here pins the
behaviour around them that survives: the melee meets the pin in reach under the retreat, a running melee outside the
retreat holds, and a lone crawler is still the crawler first's finish. The module keeps the smoke trial's frame
(`x_trial-ladder-20261109-105452`, P31-T, not evidence) and the `accept` helper the later Plan 34 and 35 tests read.

The fixtures are synthetic, built from the GUIDE's and the trial row's numbers, never a replay; the fake mod."""
from agent.base.planner import fight as F

from .fakemod import MELEE_CAPS
from .test_policies import Rig, zombie
from .test_survive_ak import ME, fight4, zm


def accept(r, a, step=None):
    """`a` accepted by the fake mod and, with `step`, one progress line of that step."""
    r.fake.act(a.aid, "accepted", a.type)
    if step is not None:
        r.fake.act(a.aid, "progress", a.type, result={"step": step})
    r.pump()


# ================================================================ the retreat's melee
def test_the_pin_in_reach_is_met_by_the_melee_as_before(tmp_path):
    """The pin at 1.2 tiles (within FIGHT_REACH) on a PZA/1.8 build: the melee goes at it, no `retreat_leg`."""
    zs = [zm(1, ME[0] + 1.2, ME[1]), zm(2, ME[0] + 3.5, ME[1]), zm(3, ME[0] + 4.0, ME[1] + 1.0)]
    r, f = fight4(tmp_path, zs, caps=MELEE_CAPS)
    cmd = f.choose()
    assert (cmd.TYPE, cmd.targetId) == ("melee", 1) and "retreat_leg" not in f.why


def test_outside_the_retreat_the_melee_holds(tmp_path):
    """No retreat: the strike melee at 1 (0.84 tiles east) with 2 come to 1.2 behind holds."""
    r, f = fight4(tmp_path, [zm(1, ME[0] + 0.84, ME[1]), zm(2, ME[0] - 1.9, ME[1])], retreat=None, target=1,
                  caps=MELEE_CAPS)
    a = f.step()
    accept(r, a, "face")
    r.frame(x=ME[0], y=ME[1], zombies=[zm(1, ME[0] + 0.84, ME[1]), zm(2, ME[0] - 1.2, ME[1])])
    f.observe()
    assert a.type == "melee" and f.busy() is True


# ================================================================ the smoke trial's frame
SMOKE_ME = (10791.28, 10629.24)   # the smoke trial's frame 1835


def sz(zid, x, y, crawler=False):
    return dict(zombie(zid, x, y, me=SMOKE_ME), crawler=crawler, onFloor=crawler)


SMOKE = [sz(9174, 10792.1, 10630.0, crawler=True), sz(9175, 10790.0, 10629.1, crawler=True),
         sz(9128, 10790.1, 10630.0), sz(9173, 10789.3, 10629.0)]


def smoke(tmp_path, zs=SMOKE, retreat=None):
    r = Rig(tmp_path, caps=MELEE_CAPS)
    r.frame(x=SMOKE_ME[0], y=SMOKE_ME[1], zombies=zs)
    f = F.Fight(r.world, r.acts, r.clock)
    f.stance, f.retreat = True, retreat
    return r, f


def test_a_lone_crawler_within_crawler_r_is_still_stomped_first(tmp_path):
    """One crawler at 0.9 tiles and a standing zombie at 3: CRAWLER_FIRST's finish as before, no `crawler_clear`."""
    zs = [sz(1, SMOKE_ME[0] + 0.9, SMOKE_ME[1], crawler=True), sz(2, SMOKE_ME[0] - 3.0, SMOKE_ME[1])]
    r, f = smoke(tmp_path, zs)
    cmd = f.choose()
    assert cmd.targetId == 1 and cmd.TYPE in ("melee", "stomp") and "crawler_first" in f.why
    assert "crawler_clear" not in f.why
