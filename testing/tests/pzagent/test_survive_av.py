"""Plan 37 Task 3 (the disposition; the spec `docs/superpowers/specs/2026-11-12-plan-37-the-disposition-design.md`
§§ 1 and 3.1): F22's death window replayed (`f_goals_22-20261111-215108`, decision lines 760 to 790: seven to eleven
standing in a lane, where the planner of the session sent six melees and six steers of the `many` run as the count
crossed RETREAT_MAX_N and back, `#4769`-`#4777`).

The replay is `replay_decisions.replay` over the artifact's own inputs to line 790 (open loop: the World follows the
recorded frames whatever the replay sends, so a line after the first moved one is counterfactual; the replay's melees
are unbound and run until a replayed send supersedes them). What it pins is the deciding layer's: one owner in
contact (no `steer`, `walkTo` or `aim` sent while a standing zombie stands within KEEP_R, so the scorer's `restarts`
reads 0 on these lines), the count crossing STRING_N sending the melee with `disposition` string and a heading, and a
release asked at the health floor (a mutation of the replay's health read) followed by the Flee only after the
hand-back or RELEASE_WAIT_S."""
import functools
import glob
import json
import math
import os
import shutil
import tempfile

import pytest

from agent.base import replay_decisions as R
from agent.base.planner import policies as P

from .frozen import runs_root

F22 = os.path.join(R.ARTIFACTS, "f_goals_22-20261111-215108")
UPTO = 790
SPAN = range(760, UPTO + 1)


def _standing_near(sv):
    """The standing zombies (not `onFloor`, not crawlers) within KEEP_R of the replayed World this tick."""
    me = sv.world.me or {}
    mx, my = me.get("x") or 0.0, me.get("y") or 0.0
    return sum(1 for z in sv.world.zombies.values()
               if z.get("x") is not None and z.get("y") is not None and z.get("onFloor") is not True
               and z.get("crawler") is not True and math.hypot(z["x"] - mx, z["y"] - my) <= P.KEEP_R)


def _replay(floor_from=None):
    """(rows, ticks): the replayed decision rows to UPTO and, per tick, (the standing within KEEP_R, the action sent
    type or None); with `floor_from` (a decision line), the health read from that line's wall on is 35.0 (under
    FLEE_HEALTH: the reflex's floor)."""
    _, rows = R.read_record(F22)
    walls = [r["wall"] for r in rows]
    ticks = []

    def mutate(sv):
        tick = sv.tick
        health = sv._health

        def wrapped(world, actions):
            near = _standing_near(sv)
            a = tick(world, actions)
            ticks.append((near, a.type if a is not None else None, a))
            return a

        sv.tick = wrapped
        if floor_from is not None:
            sv._health = lambda: 35.0 if sv.clock() >= walls[floor_from - 1] else health()

    out = R.replay(F22, mutate=mutate, upto=UPTO)
    return out, ticks


@functools.lru_cache(maxsize=1)
def replayed():
    return _replay()


def threat(row):
    return (row["inputs"].get("branches") or {}).get("threat") or {}


def test_no_steer_walk_or_aim_goes_while_a_standing_zombie_stands_within_keep_r():
    """Lines 760 to 790: every command the replay sends with a standing zombie within KEEP_R is a melee (the
    record's six steers of the `many` run, 769 to 797, are gone): the scorer's `restarts` (a work melee superseded in
    contact by a non-melee command) reads 0."""
    rows, ticks = replayed()
    sent = [(k, near, t) for k, (near, t, _) in enumerate(ticks, 1) if k in SPAN and t is not None]
    assert sent, "no command sent on the window"
    assert all(t == "melee" for k, near, t in sent if near > 0), sent
    assert not [k for k, near, t in sent if t in ("steer", "walkTo", "aim")]


def test_the_count_crossing_string_n_sends_the_melee_with_string_and_a_heading():
    """The selector's `string` on the window (the count at STRING_N or more: Task 3 fix 2, the standing closing within
    STRING_ENTRY_R or standing within GROUP_ENTRY_R, the jump taking no dwell), logged once on its line as
    `disposition` {to string}, its melee carrying `disposition` string and the withdraw heading (`string_heading`
    {deg, open, room} on the why)."""
    rows, ticks = replayed()
    changes = [(k, threat(r)["disposition"]) for k, r in enumerate(rows, 1) if k in SPAN and "disposition" in threat(r)]
    tos = [d["to"] for _, d in changes]
    assert "string" in tos and "break" not in tos
    k = next(k for k, d in changes if d["to"] == "string")
    th, (_, t, a) = threat(rows[k - 1]), ticks[k - 1]
    assert th["disposition"]["why"] in ("count", "coming")
    assert t == "melee" and a.args["disposition"] == "string"
    assert isinstance(a.args.get("withdrawX"), float) and isinstance(a.args.get("withdrawY"), float)
    assert set(th["string_heading"]) == {"deg", "open", "room"}
    later = [ticks[j - 1][2] for j in range(k, UPTO + 1) if ticks[j - 1][1] == "melee"]
    assert all(b.args["disposition"] == "string" for b in later)


def test_every_change_after_the_first_waits_the_dwell():
    """Every change on the replay waits DISPOSITION_DWELL_S but the health floor's and (Task 3 fix 2) the string's
    entry on the count's jump."""
    rows, _ = replayed()
    ds = [threat(r)["disposition"] for r in rows if "disposition" in threat(r)]
    jump = [d for d in ds if d["to"] == "string" and d["why"] in ("count", "coming")]
    assert jump and all(d["dwell"] is None or d["dwell"] >= P.DISPOSITION_DWELL_S for d in ds
                        if d["why"] != "health" and d not in jump)


def test_a_release_asked_at_the_health_floor_is_followed_by_the_flee_only_after_the_hand_back_or_the_bound():
    """The health read 35 from line 780 (a mutation): `break` at once (why health) and the engaged melee re-sent with
    `release` true; no non-melee command until the release ends (the record holds no `released` or `floor` hand-back:
    RELEASE_WAIT_S), logged `release` {asked, waited, end} on the line the rows' flee takes it."""
    rows, ticks = _replay(floor_from=780)
    k = next(k for k, r in enumerate(rows, 1) if threat(r).get("disposition", {}).get("to") == "break")
    assert k == 780 and threat(rows[k - 1])["disposition"]["why"] == "health"
    asked = [j for j in range(k, UPTO + 1) if ticks[j - 1][1] == "melee" and ticks[j - 1][2].args.get("release")]
    assert asked and asked[0] == k
    hand = next(j for j in range(k, UPTO + 1) if "release" in threat(rows[j - 1]))
    rel = threat(rows[hand - 1])["release"]
    assert rel["end"] == "bound" and rel["waited"] >= P.RELEASE_WAIT_S
    assert all(ticks[j - 1][1] in (None, "melee") for j in range(k, hand))
    assert ticks[hand - 1][1] not in (None, "melee") and threat(rows[hand - 1]).get("flee") is not None


# ================================================================ Task 3 fix 3: round one's horde8 trial
# `x_trial-ladder-20261112-061307` (P31-T, not evidence; at 91b18c57): replayed from this machine's run folder
# (`testing/runs/` is per-machine and gitignored, so skipped where absent; `test_survive_ah.py`'s style: the admin state
# log and the decision log copied to a temporary artifact folder), open loop to line 205.
TRIAL = "x_trial-ladder-20261112-061307"


@functools.lru_cache(maxsize=1)
def trial():
    """(rows, ticks) of the trial's replay to line 205 (`_replay`'s shape), skipped where the run is absent."""
    root = os.path.join(runs_root() or "", TRIAL)
    logs = glob.glob(os.path.join(root, "clients", "admin", "Lua", "pzagent", "*", "state.log"))
    if not logs:
        pytest.skip("%s is not on this machine (testing/runs/ is per-machine)" % TRIAL)
    ticks = []

    def mutate(sv):
        tick = sv.tick

        def wrapped(world, actions):
            near = _standing_near(sv)
            a = tick(world, actions)
            ticks.append((near, a.type if a is not None else None, a))
            return a
        sv.tick = wrapped
    with tempfile.TemporaryDirectory() as d:
        shutil.copy(logs[0], os.path.join(d, "state.log"))
        shutil.copy(os.path.join(root, "decision.log"), os.path.join(d, "decision.log"))
        rows = R.replay(d, mutate=mutate, upto=205)
    return rows, ticks


def test_the_trial_s_contact_lines_send_no_steer():
    """Fix 3 (2), the contract: lines 145 to 201 (the clump, game minutes 597 to 604), where the trial sent the drag
    guard's `many` steers at lines 153 and 157 between melees: every command the replay sends with a standing zombie
    within KEEP_R is a melee; 153 and 157 send no steer."""
    rows, ticks = trial()
    sent = [(k, near, t) for k, (near, t, _) in enumerate(ticks, 1) if 145 <= k <= 201 and t is not None]
    assert sent and all(t == "melee" for k, near, t in sent if near > 0), sent
    assert ticks[152][1] != "steer" and ticks[156][1] != "steer"


def test_the_trial_s_clump_enters_the_string():
    """Fix 3 (1): the hold inside the clump (the nearest never beyond STRING_MIN_GAP) enters `string` on the window,
    why `crowd` or `pinned`."""
    rows, _ = trial()
    ds = [threat(r)["disposition"] for k, r in enumerate(rows, 1) if 140 <= k <= 201 and "disposition" in threat(r)]
    assert any(d["to"] == "string" and d["why"] in ("crowd", "pinned") for d in ds), ds


def test_the_trial_s_bleed_finds_nothing_to_rip_and_says_so():
    """Fix 3 (3), the reading: from the line the scratch first bleeds (176, game minute 601) every cotton garment the
    character holds is worn (the mini skirt, the boob tube; an unwear stops on a walk), so no rip can ride the engaged
    melee: each line logs `care_ride` {cmd null, why "worn"} under the running disposition, and no care command goes."""
    rows, ticks = trial()
    rides = [threat(r).get("care_ride") for k, r in enumerate(rows, 1) if 176 <= k <= 201]
    assert rides and all(c is not None and c["cmd"] is None and c["why"] == "worn" for c in rides)
    assert all(ticks[k - 1][1] in (None, "melee") for k in range(176, 202))
