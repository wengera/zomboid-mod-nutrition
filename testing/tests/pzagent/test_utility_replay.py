"""The situation utility replayed over committed rings (Plan 31 Task 11 U; `agent.base.planner.utility.replay`): the
doctrine at the situations the rings carry, and the regression goldens `fixtures/survive-utility-<key>.json` with
their mutation pass.

Open loop (the replay's THE ACTS): the World follows the recorded frames whatever the utility sends, so these check
decisions at recorded situations, never outcomes. The doctrine's checks read the line's own logged scores: its
fresh choice (`top`: the best eligible, unvetoed candidate by its total, the commitment aside) and its committed act.

- an aware standing zombie within KEEP_R while armed, its fight not vetoed -> the act is a fight, on every line of
  F15, E23 and F6 (fix 1, review-t11-utility M4: no line skipped for a group listed or a spent character);
- a bleeding part with no standing zombie within KEEP_R (fewer than three aware listed), the dress not vetoed -> the
  fresh choice is the dress or a fight (never the goal, the needs, a retreat or the rest);
- a group arriving, read off the frame by an oracle of the test's own (`closing_group`: three or more aware standing
  zombies listed, closing, reachable: no known blocked edge between, no `unreachable` mark), never the decider's own
  `utility.group` flag -> no goal walk, loot, sneak or needs, ever (fix 1, M1, the refuge ruling; fix 3, the ruling
  (a) on review-t11-utility-fix2: a group is avoided before it arrives, closing beyond DANGER_R included); with no
  filter the act is the stand or a fight at one in reach (E23 404-413, 470-475 and 517-522, F15 326, 327, 626 and
  663-667 named; F6 331 and 535 read no group, a third closing zombie across a blocked edge); a stand only under a
  group the decider reads (its own flag, the recede clock's);
- three or more aware standing within DANGER_R with an eligible retreat to a filter -> the fresh choice is the
  retreat or a fight in reach, and the act follows it within one selection; every retreat on every line names a door
  square and the threat's `flee` "retreat:door" (F6 carries the group at the door; F15 and E23 carry none);
- a zombie within DOOR_HELD_R behind a portal (`door_held.portal_between`) -> the line sends or holds its own
  action (fix 2, review-t11-utility-fix1 M3: the send read); a goal act on a line whose record sent no goal command is
  the replay's blind spot, the judged and the blind lines pinned per ring (fix 3).
"""
import json
import os

import pytest

from agent.base.planner.door_held import portal_between
from agent.base.planner.edges import edge_read
from agent.base.planner.policies import DANGER_R, DISENGAGE_R, DOOR_HELD_R, KEEP_R, LISTED_R
from agent.base.planner.utility import acts as A
from agent.base.planner.utility import replay as R
from agent.base.planner.utility import select as S
from agent.base.replay_decisions import read_record

F6 = "f_goals_7-20261031-000629"   # F6: the group at building 2's door (lines 486 and 487), its first 600 lines
F6_UPTO = 600
RINGS = {"f15": (R.RUNS["f15"], None), "e23": (R.RUNS["e23"], None), "f6": (F6, F6_UPTO)}


def _run(key, mutate=None):
    name, upto = RINGS[key]
    return R.replay(os.path.join(R.ARTIFACTS, name), mutate=mutate, upto=upto)


@pytest.fixture(scope="module")
def replayed():
    return {key: _run(key) for key in RINGS}


@pytest.fixture(scope="module")
def situations():
    out = {}
    for key, (name, upto) in RINGS.items():
        lines, rows = read_record(os.path.join(R.ARTIFACTS, name))
        rows = rows if upto is None else rows[:upto]
        rec = []
        for k, row, sit, world in R.situations(lines, rows, fresh_only=False):   # the selector's own view
            me = (sit.x, sit.y)
            door = any(z.d <= DOOR_HELD_R and portal_between(world, me, (z.x, z.y), world.marked_doors(), sit.on_room)
                       is not None for z in sit.zeds)
            closing = [z.id for z in sit.aware_standing(LISTED_R) if z.closing > 0.0 and not _blocked(world, sit, z)]
            rec.append((k, sit, door, closing))
        out[key] = rec
    return out


def _blocked(world, sit, z):
    """A known blocked edge with no door passing it between the player and `z` (`edges.edge_read`)."""
    read = edge_read(world, (sit.x, sit.y), (z.x, z.y), DISENGAGE_R, marked=world.marked_doors())
    return read is not None and read["via"] is None


def closing_group(u, closing):
    """The oracle: three or more aware, closing, reachable zombies listed off the frame (`situations`), less those the
    line's own vetoes mark `unreachable` (the planner's marks, which the frame does not carry)."""
    return len([z for z in closing if u["vetoes"].get("fight:%s" % z) not in ("unreachable", "blocked_edge")]) >= 3


def top(u):
    """The line's fresh choice: the best eligible, unvetoed candidate by its logged total (`select.eligible`)."""
    best = None
    for k, (tot, _) in sorted(u["scores"].items()):
        if k in u["vetoes"] or (k.startswith("retreat") and tot <= S.RETREAT_FLOOR):
            continue
        if best is None or tot > best[0]:
            best = (tot, k)
    return None if best is None else best[1]


def _u(replayed, key, k):
    return replayed[key][k - 1]["inputs"]["utility"]


# ================================================================ the doctrine
@pytest.mark.parametrize("key", list(RINGS))
def test_an_aware_zombie_in_reach_is_fought_on_every_line(replayed, situations, key):
    n = 0
    for k, sit, _, _ in situations[key]:
        reach = sit.aware_standing(KEEP_R)
        if not sit.armed or not reach:
            continue
        u = _u(replayed, key, k)
        if all(u["vetoes"].get("fight:%s" % z.id) is not None for z in reach):
            continue   # every fight in reach infeasible (an edge between, the door left): the vetoes' lines
        n += 1
        act = u["act"] or ""
        assert act.startswith("fight:"), (key, k, act, u["select"], u["held_by"])
        target = sit.zed(u["target"])   # fix 2 (review-t11-utility-fix1 M1): the zombie in reach, never a farther one
        assert target is not None and target.d <= KEEP_R, (key, k, act, None if target is None else target.d)
    assert n >= 50, n


@pytest.mark.parametrize("key", ["f15", "e23"])
def test_a_bleeding_part_with_nothing_in_reach_is_dressed_before_the_goal_or_any_retreat(replayed, situations, key):
    n = 0
    for k, sit, _, _ in situations[key]:
        ns = sit.nearest_standing()
        if not sit.bleeding or (ns is not None and ns.d <= KEEP_R) or len(sit.aware_standing(LISTED_R)) >= 3:
            continue
        u = _u(replayed, key, k)
        if "dress:%d" % sit.bleeding[0].i in u["vetoes"] or u["group"]:
            continue   # the dress vetoed, or the recede clock's window (fix 3): the group's, the stand's lines
        n += 1
        assert (top(u) or "").split(":")[0] in ("dress", "fight"), (key, k, top(u))
    assert n >= 10, n


WALKS = ("travel", "loot", "sneak", "needs")


@pytest.mark.parametrize("key", list(RINGS))
def test_no_walk_away_from_an_arriving_group(replayed, situations, key):
    """The oracle off the frame (`closing_group`), never the decider's flag: under three or more aware, closing,
    reachable zombies no walk is chosen or offered (fix 3, the ruling (a)). And a stand only under a group the decider
    reads (its flag, the recede clock's: a stand of about STAND_RECEDE_S before a group that recedes is accepted)."""
    n = 0
    for k, sit, _, closing in situations[key]:
        u = _u(replayed, key, k)
        if u["kind"] == "stand":
            assert u["group"], (key, k, u["act"])
        if not closing_group(u, closing):
            continue
        n += 1
        assert (u["act"] or "").split(":")[0] not in WALKS and not set(u["scores"]) & set(WALKS), (key, k, u["act"])
    assert n >= 1


@pytest.mark.parametrize("key, lines", [("f15", [626, 663, 664, 665, 666, 667]), ("e23", list(range(404, 414))),
                                        ])   # F6 331 and 535 read no group: each one's third closing zombie lies
                                             # across a known blocked edge (21725 at 331, 21710 at 535, which the
                                             # planner marks unreachable by 537); two can come
def test_the_closing_groups_are_met_where_the_character_stands(replayed, situations, key, lines):
    """Review-t11-utility-fix2's lines (walks under a closing group before fix 3): the stand, or the fight at one in
    reach."""
    sits = {k: sit for k, sit, _, _ in situations[key]}
    for k in lines:
        u = _u(replayed, key, k)
        kind = u["kind"]
        assert kind == "stand" or (kind == "fight" and sits[k].zed(u["target"]).d <= KEEP_R), (key, k, u["act"])


@pytest.mark.parametrize("key", list(RINGS))
def test_no_stand_at_a_zombie_that_cannot_come(replayed, key):
    """Review-t11-utility-fix1 M2 (F6 330-332 and 570-576 stood at a target across a blocked edge or marked
    unreachable): a stand's target is never one whose fight is vetoed so."""
    for rep in replayed[key]:
        u = rep["inputs"]["utility"]
        if u["kind"] == "stand":
            assert u["vetoes"].get("fight:%s" % u["target"]) not in ("blocked_edge", "unreachable"), (key, u["act"])


def _walk_back_within_the_clock(replayed, key, k):
    """The first line from `k` on whose act is no stand comes within STAND_RECEDE_S (and one selection) of line k's
    wall, and offers a walk: the ruling (a)'s accepted stand of about STAND_RECEDE_S before a receding group."""
    rows = replayed[key]
    j = next(j for j in range(k - 1, len(rows)) if rows[j]["inputs"]["utility"]["kind"] != "stand")
    assert rows[j]["wall"] - rows[k - 1]["wall"] <= A.STAND_RECEDE_S + S.SELECT_S, (key, k, j + 1)
    assert set(rows[j]["inputs"]["utility"]["scores"]) & set(WALKS), (key, j + 1)


def test_the_walks_return_when_the_group_recedes(replayed):
    """F6 478-481: the target receding from 7.5 to 10.8 tiles; past STAND_RECEDE_S the stand ends, the goal returns."""
    _walk_back_within_the_clock(replayed, "f6", 478)


@pytest.mark.parametrize("key, lines", [("e23", list(range(470, 476)) + list(range(517, 523))),
                                        ("f15", [326, 327])])
def test_the_review_s_lines_meet_the_group_where_the_character_stands(replayed, key, lines):
    for k in lines:
        act = _u(replayed, key, k)["act"] or ""
        assert act.split(":")[0] in ("stand", "fight"), (key, k, act)


@pytest.mark.parametrize("k", [476, 523])
def test_e23_s_groups_recede_and_the_walk_returns(replayed, k):
    """Fix 2 (review-t11-utility-fix1 M2), fix 3's clock: E23 476 and 523, every aware zombie beyond DANGER_R receding:
    the stand held the recede clock's window at most, then the walk."""
    _walk_back_within_the_clock(replayed, "e23", k)


@pytest.mark.parametrize("k", [280, 326])
def test_the_held_fights_at_f15_280_and_326_stay_fights(replayed, k):
    assert (_u(replayed, "f15", k)["act"] or "").startswith("fight:")


def _in_reach(sit, key):
    return key.startswith("fight:") and sit.zed(int(key.split(":")[1])).d <= KEEP_R


def test_a_group_with_a_filter_is_retreated_from_to_the_door_or_struck_in_reach(replayed, situations):
    """The fresh choice is the retreat or a fight in reach; the act follows it within one selection (`cadence`), or
    the stand taken before the filter came holds its span."""
    retreats = 0
    for k, sit, _, _ in situations["f6"]:
        if len(sit.aware_standing(DANGER_R)) < 3:
            continue
        u = _u(replayed, "f6", k)
        if not any(key.startswith("retreat") and tot > S.RETREAT_FLOOR and key not in u["vetoes"]
                   for key, (tot, _) in u["scores"].items()):
            continue
        t, act = top(u) or "", u["act"] or ""
        assert t.startswith("retreat") or _in_reach(sit, t), (k, t)
        retreats += act.startswith("retreat")
        held = u["held_by"] == "cadence" or (u["held_by"] == "span" and act.startswith("stand:"))
        assert act.startswith("retreat") or _in_reach(sit, act) or held, (k, act, u["held_by"])
    assert retreats >= 1


@pytest.mark.parametrize("key", list(RINGS))
def test_every_retreat_names_its_door_and_reads_as_a_retreat_on_the_line(replayed, key):
    for rep in replayed[key]:
        u = rep["inputs"]["utility"]
        if u["kind"] != "retreat":
            continue
        intent = rep["inputs"]["intent"]
        assert intent["kind"] == "retreat:door" and isinstance(intent["target"], list) and len(intent["target"]) == 2
        assert rep["branch"] == "threat" and rep["inputs"]["branches"]["threat"]["flee"] == "retreat:door"


GOAL_ACTS = ("travel", "loot", "sneak")


def _record_rows(key):
    name, upto = RINGS[key]
    _, rows = read_record(os.path.join(R.ARTIFACTS, name))
    return rows if upto is None else rows[:upto]


def waits(rep):
    """The line sends nothing and holds no action of its own (no `holding` aid, no maneuver running): a wait."""
    if rep["action"] is not None:
        return False
    whys = [v for v in (rep["inputs"].get("branches") or {}).values() if isinstance(v, dict)]
    return not any(v.get("holding") is not None or v.get("maneuver") is not None for v in whys)


@pytest.mark.parametrize("key", ["e23", "f6"])
def test_a_zombie_behind_a_door_is_never_waited_on(replayed, situations, key, capsys):
    """Fix 2 (review-t11-utility-fix1 M3): the send read, never the act. A goal act on a line whose record sent no goal
    command is the replay's blind spot (the runner's answer there is unknown: `replay.ReplayGoals`), counted and named,
    never passed as a send."""
    rows = _record_rows(key)
    judged, blind = [], []
    for k, _, door, _ in situations[key]:
        if not door:
            continue
        rep = replayed[key][k - 1]
        u = rep["inputs"]["utility"]
        rec = rows[k - 1]
        if (u["kind"] in GOAL_ACTS and rep["action"] is None
                and not (rec.get("branch") == "goal" and rec.get("sent"))):
            blind.append(k)
            continue
        judged.append(k)
        assert u["act"] is not None and u["act"] != "rest" and not waits(rep), (key, k, u["act"], u["select"])
    with capsys.disabled():
        print("\ndoor lines %s: %d judged %s, %d blind %s" % (key, len(judged), judged, len(blind), blind[:20]))
    assert (judged, blind if key == "e23" else len(blind)) == DOOR_LINES[key]   # fix 3: pinned, never vacuous


DOOR_LINES = {"e23": ([563], [132, 133]), "f6": ([], 72)}   # the judged lines and the blind ones (fix 3, review-t11-
                                                           # utility-fix2 finding 3: E23 563 judged; F6 all blind)


def test_no_line_sprints(replayed):
    for key in RINGS:
        for rep in replayed[key]:
            assert ((rep["action"] or {}).get("args") or {}).get("gait") != "sprint"


# ================================================================ the goldens and their mutation pass
def golden(key):
    with open(R.golden_path(key), encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("key", sorted(R.RUNS))
def test_the_golden_reproduces_byte_for_byte(replayed, key):
    g = golden(key)
    assert g["artifact"] == R.RUNS[key]
    got = R.golden_text(R.decisions(replayed[key]), g["base"], g["artifact"], g["recorded"])
    with open(R.golden_path(key), encoding="utf-8", newline="") as f:
        assert f.read() == got


def _sign(term, v):
    def m(monkeypatch):
        monkeypatch.setitem(S.TERM_SIGN, term, v)
    return m


def _delta0(monkeypatch):
    monkeypatch.setattr(S, "DELTA0", 0.0)
    monkeypatch.setattr(S, "DELTA_FRAC", 0.0)


MUTATIONS = {"chase sign flipped": _sign("chase", -1.0), "hit sign flipped": _sign("hit", -1.0),
             "kill dropped": _sign("kill", 0.0), "hit dropped": _sign("hit", 0.0), "bleed dropped": _sign("bleed", 0.0),
             "goal dropped": _sign("goal", 0.0), "regress dropped": _sign("regress", 0.0), "delta 0": _delta0}


def moved(key, rows):
    """(lines whose decision moved: branch, action or act; lines whose pinned scores, margin or commitment moved)."""
    g = golden(key)["decisions"]
    dec = sum(1 for a, b in zip(g, rows)
              if (a["branch"], a["action"], a["act"]) != (b["branch"], b["action"], b["act"]))
    any_ = sum(1 for a, b in zip(g, rows) if a != b)
    return dec, any_


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_each_mutation_moves_a_pinned_line(name, monkeypatch, capsys):
    MUTATIONS[name](monkeypatch)
    tally = {key: moved(key, R.decisions(R.replay(R.run_dir(key)))) for key in sorted(R.RUNS)}
    with capsys.disabled():
        print("\nmutation %r: %s" % (name, tally))
    assert sum(a for _, a in tally.values()) > 0, tally
    if name in INERT:   # the term no golden line's decision reads: the artifact reports its weight flat
        assert sum(d for d, _ in tally.values()) == 0 and INERT[name] in _flat(), (name, tally)
    else:
        assert sum(d for d, _ in tally.values()) > 0, tally   # fix 1 (M5): the decisions themselves move


INERT = {"regress dropped": "G"}   # the regress decides no golden line (no retreat on F15 or E23): G reads flat


def _flat():
    with open(os.path.join(R.REPO, "data", "fits", "utility-weights.json"), encoding="utf-8") as f:
        return json.load(f)["decision_probes"]["flat"]
