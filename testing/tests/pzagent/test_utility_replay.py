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
- a group arriving (three or more aware standing listed) -> no goal walk, loot, sneak or needs, ever (fix 1, M1, the
  refuge ruling); with no filter the act is the stand or a fight (E23 470-477 and 517-524, F15 326 and 327 named);
- three or more aware standing within DANGER_R with an eligible retreat to a filter -> the fresh choice is the
  retreat or a fight in reach, and the act follows it within one selection; every retreat on every line names a door
  square and the threat's `flee` "retreat:door" (F6 carries the group at the door; F15 and E23 carry none);
- a zombie within DOOR_HELD_R behind a portal (`door_held.portal_between`) -> the line's own act is never none and
  never the rest: no wait (fix 1, M4: an act passed over with nothing sent fails it).
"""
import json
import os

import pytest

from agent.base.planner.door_held import portal_between
from agent.base.planner.policies import DANGER_R, DOOR_HELD_R, KEEP_R, LISTED_R
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
            rec.append((k, sit, door))
        out[key] = rec
    return out


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
    for k, sit, _ in situations[key]:
        reach = sit.aware_standing(KEEP_R)
        if not sit.armed or not reach:
            continue
        u = _u(replayed, key, k)
        if all(u["vetoes"].get("fight:%s" % z.id) is not None for z in reach):
            continue   # every fight in reach infeasible (an edge between, the door left): the vetoes' lines
        n += 1
        assert (u["act"] or "").startswith("fight:"), (key, k, u["act"], u["select"], u["held_by"])
    assert n >= 50, n


@pytest.mark.parametrize("key", ["f15", "e23"])
def test_a_bleeding_part_with_nothing_in_reach_is_dressed_before_the_goal_or_any_retreat(replayed, situations, key):
    n = 0
    for k, sit, _ in situations[key]:
        ns = sit.nearest_standing()
        if not sit.bleeding or (ns is not None and ns.d <= KEEP_R) or len(sit.aware_standing(LISTED_R)) >= 3:
            continue
        u = _u(replayed, key, k)
        if "dress:%d" % sit.bleeding[0].i in u["vetoes"]:
            continue
        n += 1
        assert (top(u) or "").split(":")[0] in ("dress", "fight"), (key, k, top(u))
    assert n >= 10, n


WALKS = ("travel", "loot", "sneak", "needs")


@pytest.mark.parametrize("key", list(RINGS))
def test_no_walk_away_from_an_arriving_group(replayed, situations, key):
    n = 0
    for k, sit, _ in situations[key]:
        if len(sit.aware_standing(LISTED_R)) < 3:
            continue
        n += 1
        u = _u(replayed, key, k)
        assert (u["act"] or "").split(":")[0] not in WALKS and not set(u["scores"]) & set(WALKS), (key, k, u["act"])
    assert n >= 1


@pytest.mark.parametrize("key, lines", [("e23", list(range(470, 478)) + list(range(517, 525))),
                                        ("f15", [326, 327])])
def test_the_review_s_lines_meet_the_group_where_the_character_stands(replayed, key, lines):
    for k in lines:
        act = _u(replayed, key, k)["act"] or ""
        assert act.split(":")[0] in ("stand", "fight"), (key, k, act)


@pytest.mark.parametrize("k", [280, 326])
def test_the_held_fights_at_f15_280_and_326_stay_fights(replayed, k):
    assert (_u(replayed, "f15", k)["act"] or "").startswith("fight:")


def _in_reach(sit, key):
    return key.startswith("fight:") and sit.zed(int(key.split(":")[1])).d <= KEEP_R


def test_a_group_with_a_filter_is_retreated_from_to_the_door_or_struck_in_reach(replayed, situations):
    """The fresh choice is the retreat or a fight in reach; the act follows it within one selection (`cadence`), or
    the stand taken before the filter came holds its span."""
    retreats = 0
    for k, sit, _ in situations["f6"]:
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


@pytest.mark.parametrize("key", ["e23", "f6"])
def test_a_zombie_behind_a_door_is_never_waited_on(replayed, situations, key):
    n = 0
    for k, _, door in situations[key]:
        if not door:
            continue
        n += 1
        u = _u(replayed, key, k)
        assert u["act"] is not None and u["act"] != "rest", (key, k, u["select"], u.get("passed"))
    assert n >= 1


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
