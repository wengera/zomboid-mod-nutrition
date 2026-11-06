"""tools/trial_score.py (Plan 31 Task 7): the trials' scorecard, on F15's committed artifact (one case per reading, the
expected values computed by hand from its logs as each docstring says) and on synthetic rings (one per new reading,
exercising its rule), with the row's shape, `--dry`, the in-place replace and `--rescore-all` keeping the `seen` text.

F15 is `testing/artifacts/f_goals_16-20261105-164332/` (Plan 30's fifteenth LLM session: no kill, six hit reactions
and eight landed attacks, a death at game minute 702). Its hand computations were plain scripts over the files with
`json` and `gates_e.session_lines` only, none of this tool's functions: the decision log's 1044 lines read as JSON
objects, the state log's 12897 lines decoded (5423 frames)."""
import json
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import trial_score as TS  # noqa: E402

REPO = TS.REPO
from agent.base import gates_e as E  # noqa: E402
from agent.base import pza1  # noqa: E402

F15 = os.path.join(REPO, "testing", "artifacts", "f_goals_16-20261105-164332")
TRIALS = os.path.join(REPO, "testing", "trials", "trials.md")


@pytest.fixture(scope="module")
def f15():
    return TS.score(F15)


# ================================================================ F15: the imported readers
def test_f15_the_kills_hits_end_health_and_minutes_read_as_its_grade_reads_them(f15):
    """F15's `f_grade.txt` (grade_f12 at the artifact): `kills matched` the events [] and 0 matched, `hits union` 6
    reaction runs, 6 hit step runs, 8 attacks landed; the record's `stop` {reason death, gameMin 702}; the loop's
    `first_game_min` 560 and `game_min` 702 (142 minutes); the last frame by wall (seq 12813's death) reads
    `body.health` 0; `goal wait` 27 pending lines unmoved near a zombie, 13.500 s; `standing` 0 stretches."""
    assert f15["kills_events"] == 0 and f15["kills_matched"] == 0
    assert (f15["hits"]["runs"], f15["hits"]["steps"], f15["hits"]["union"]) == (6, 6, 8)
    assert f15["end"] == "death@702"
    assert f15["health"] == 0
    assert f15["minutes"] == 142
    assert f15["goal_wait"]["unmoved_near_s"] == 13.5
    assert f15["standing"]["stretches"] == 0
    assert f15["trial"] is None                         # no trial.json beside an old run


# ================================================================ F15: the four new readings
def test_f15_flee_minutes_are_its_298_flee_lines_39_27_game_minutes_over_138_51(f15):
    """By hand: 298 of the 1044 decision lines carry `inputs.branches.threat.flee` non-null (held 146, pair 60, flip
    36, unreachable 24, health 21, many 11); the minutes are the next line's `inputs.hour` x 60 less the line's over
    those lines, the log's last line (a flee line) standing for none: 39.26645 game minutes, 149.408 wall seconds; the
    log runs from 563.38457 to 701.89722, 138.51265 game minutes. F15 has no variant's intent, play or act key."""
    fl = f15["flee"]
    assert fl["lines"] == 298
    assert fl["minutes"] == pytest.approx(39.26645, abs=1e-4)
    assert fl["seconds"] == pytest.approx(149.408, abs=1e-2)
    assert fl["total_minutes"] == pytest.approx(138.51265, abs=1e-4)
    assert fl["by"] == {"flee:held": 146, "flee:pair": 60, "flee:flip": 36, "flee:unreachable": 24,
                        "flee:health": 21, "flee:many": 11}


def test_f15_toward_minutes_are_130_lines_17_26_game_minutes_of_223_naming_a_target(f15):
    """By hand: the goal-branch lines whose goal's args carry x and y (124 ExploreToward lines among 328 goal lines;
    44 LootBuilding and 4 Stock name no square) or, on a model wait, the goal why's `goal_continue.target`: 223 lines
    after the first, 29.38311 game minutes from each line before; of them 130 whose position lies more than 0.05 tiles
    nearer the target than the line before's (79 ExploreToward, 51 continued walks), 17.25637 game minutes."""
    tw = f15["toward"]
    assert (tw["lines"], tw["named_lines"]) == (130, 223)
    assert tw["minutes"] == pytest.approx(17.25637, abs=1e-4)
    assert tw["named_minutes"] == pytest.approx(29.38311, abs=1e-4)
    assert tw["by"] == {"ExploreToward": 79, "continue": 51}


def test_f15_dressed_reads_none_of_its_six_bleeds_stopped_within_a_game_minute(f15):
    """By hand over the 5423 frames in wall order, `body.parts[i].bleeding` false-to-true: part 0 at seq 1760, part 2
    at 1796, part 1 at 1857, part 2 again at 11327, part 8 at 11673, part 5 at 12355, six wounds; only part 2's first
    stops, at seq 2030, 4.655 game minutes later by `me.hour`, bandaged; the other five bleed to the death. 0 of 6."""
    dr = f15["dressed"]
    assert (dr["dressed"], dr["wounds"], dr["stopped"]) == (0, 6, 1)
    assert [(r["part"], r["seq0"], r["seq1"]) for r in dr["rows"]] == [
        (0, 1760, None), (2, 1796, 2030), (1, 1857, None), (2, 11327, None), (8, 11673, None), (5, 12355, None)]
    assert dr["rows"][1]["minutes"] == pytest.approx(4.65517, abs=1e-4)
    assert dr["rows"][1]["bandaged"] is True


def test_f15_one_of_26_melees_was_superseded_before_any_press_and_19_superseded_in_all(f15):
    """By hand over the state log's melee act lines by aid: 26 melees (the record's loop.actions 26 of type melee),
    19 ending `failed` `superseded` (f_grade.txt's melee line: ends {'failed superseded': 19, 'done time': 7}); of the
    19, one (a218) has no progress step among swing, shove, stomp and floor, and four have no `swing` step (three of
    them a finish's floor swing)."""
    ml = f15["melees"]
    assert (ml["superseded_before"], ml["sent"], ml["superseded"], ml["no_swing_step"]) == (1, 26, 19, 4)
    assert ml["aids"] == ["a218"]


def test_f15_the_row_reads_every_cell_in_the_logs_column_order(f15):
    """The row against the committed log's header: 15 cells, the trial cells `-` with no trial.json."""
    head, _ = TS.read_log(TRIALS)
    header = TS.parse_row(head[-2])
    assert tuple(header) == TS.COLUMNS
    cs = TS.cells(f15, "seen one / two")
    assert len(cs) == len(TS.COLUMNS)
    assert cs == ["f_goals_16-20261105-164332", "-", "-", "-", "142", "0", "6 / 8", "-", "39.3 / 138.5 (away 41.1)",
                  "17.3 / 138.5", "0 / 6", "1 / 26 (19 superseded)", "death@702", "0", "seen one / two"]


def test_f15_away_minutes_legs_and_labels_read_as_by_hand(f15):
    """By hand (a script over the frames in wall order with json and `gates_e.session_lines` only): of the frame
    pairs where the character moved more than 0.05 tiles and the nearest `hasTarget` zombie of the first frame is
    listed on the second more than 0.05 tiles farther, 1551 qualify; 6 lie under a decision line naming a refuge (the
    threat why's `shelter` set, or a `doorway_pick` other than `no_door`; `leg: enter`, the melee stance's entry leg,
    names none: review-t7-fix1 R1), leaving 1545 intervals, 41.01505 game minutes by `me.hour` with five steps back
    (-0.10706 min) counted, 41.12211 with them counted 0 (the reviewer's 41.122). The ladder's legs
    off the threat why's `leg`, each line to the next: pull 152 lines 20.34473 min, back 90 lines 11.99976 min (the
    reviewer's 20.34 and 12.00). No line carries `intent`, `play` or `act`: no label, no play target."""
    aw = f15["away"]
    assert (aw["intervals"], aw["refuge_skipped"]) == (1545, 6)
    assert aw["minutes"] == pytest.approx(41.12211, abs=1e-4)
    assert f15["legs"]["pull"]["lines"] == 152 and f15["legs"]["back"]["lines"] == 90
    assert f15["legs"]["pull"]["minutes"] == pytest.approx(20.34473, abs=1e-4)
    assert f15["legs"]["back"]["minutes"] == pytest.approx(11.99976, abs=1e-4)
    assert f15["labels"] == {} and f15["toward"]["unresolved"] == 0
    d = "\n".join(TS.detail(f15))
    assert "leg: pull 152 lines 20.34 min, leg: back 90 lines 12.00 min" in d
    assert "1545 intervals, 41.12 game minutes over 138.51 (6 intervals under a refuge skipped)" in d


# ================================================================ synthetic rings, one per new reading
def _line(hour, x=0.0, y=0.0, branch="threat", wall=None, threat=None, goal=None, gwhy=None, **kw):
    r = {"branch": branch, "wall": wall if wall is not None else hour * 3600.0, "goal": goal,
         "inputs": {"hour": hour, "x": x, "y": y, "branches": {"threat": threat or {}, "goal": gwhy or {}}}}
    r.update(kw)
    return r


def test_flee_counts_the_ladders_flee_lines_and_a_variants_retreat_labels_each_to_the_next_line():
    """The rule: a line whose threat why's `flee` is set, or whose `intent`/`play`/`act` (the line's or its inputs',
    a string or a dict's kind) starts avoid, kite or retreat, stands from its own game minute to the next line's; a
    fight line, an `attack` play and a dict naming `strike` count nothing; the log's last line stands for none; the
    hour unwraps past midnight (23.95 h to 0.05 h is 6 game minutes)."""
    m = 1.0 / 60.0
    rows = [_line(10.0, threat={"flee": "pair"}),                 # 1 min
            _line(10.0 + m, threat={"fight": True}),              # a fight: no
            _line(10.0 + 2 * m, play="retreat_filter"),           # 2 min
            _line(10.0 + 4 * m, intent={"kind": "Kite"}),         # 1 min, a dict's kind, any case
            _line(10.0 + 5 * m, play="attack"),                   # no
            _line(10.0 + 6 * m, act={"kind": "strike"}),          # no
            _line(23.95, threat={"flee": "many"}),                # to 0.05 h: 6 min past midnight
            _line(0.05),                                          # an inputs-level act (below): 0 min to the next
            _line(0.05, threat={"flee": "held"})]                 # the last line: none
    rows[7]["inputs"]["act"] = "avoid_three"
    fl = TS.flee_minutes(rows)
    assert fl["lines"] == 6
    assert fl["minutes"] == pytest.approx(1 + 2 + 1 + 6 + 0, abs=1e-6)
    assert fl["by"] == {"flee:pair": 1, "retreat_filter": 1, "kite": 1, "flee:many": 1, "avoid_three": 1,
                        "flee:held": 1}
    assert TS.flee_minutes([]) == {"lines": 0, "minutes": 0.0, "seconds": 0.0, "total_minutes": 0.0, "by": {}}


def _frame_line(seq, wall_ms, zombies=()):
    return {"kind": "frame", "seq": seq, "wallMs": wall_ms, "me": {"x": 0, "y": 0},
            "zombies": [{"id": z, "x": x, "y": y} for z, x, y in zombies]}


def test_toward_counts_a_line_whose_distance_to_its_named_target_fell_past_the_drift():
    """The rule: a goal-branch line with its goal's args square, a continued walk's target or a play's target (a
    square, or a zombie id on the frame at the line) counts the minutes since the line before when the position fell
    more than MOVE_EPS nearer it; a rise, a drift under MOVE_EPS, a threat-branch line under a goal's square, a
    LootBuilding with no square and a play's zombie absent from the frame count nothing as toward (the last two name
    no target)."""
    m = 1.0 / 60.0
    explore = {"type": "ExploreToward", "args": {"x": 10, "y": 0}, "state": "running"}
    rows = [_line(10.0, x=0.0, branch="goal", goal=explore),
            _line(10.0 + m, x=1.0, branch="goal", goal=explore),                  # 9 from 10: toward, 1 min
            _line(10.0 + 2 * m, x=0.5, branch="goal", goal=explore),              # rose: named, not toward
            _line(10.0 + 3 * m, x=0.52, branch="goal", goal=explore),             # 0.02: drift
            _line(10.0 + 4 * m, x=2.0, branch="threat", goal=explore),            # threat branch: no target
            _line(10.0 + 6 * m, x=3.0, branch="goal", goal={"pending": "llm"},    # continued walk, 2 min
                  gwhy={"goal_continue": {"source": "edge", "target": [10, 0]}}),
            _line(10.0 + 7 * m, x=4.0, branch="goal", goal={"type": "LootBuilding", "args": {"building": 2}}),
            _line(10.0 + 8 * m, x=5.0, play={"kind": "fight", "target": 77}),     # zombie 77 at (9, 0): 1 min
            _line(10.0 + 9 * m, x=6.0, play={"kind": "fight", "target": 78})]     # 78 not listed: no target
    lines = [_frame_line(1, rows[7]["wall"] * 1000.0, zombies=[(77, 9, 0)]),
             _frame_line(2, rows[8]["wall"] * 1000.0)]
    L = E._Lines({}, rows, lines)
    tw = TS.toward_minutes(L)
    assert tw["lines"] == 3
    assert tw["minutes"] == pytest.approx(1 + 2 + 1, abs=1e-6)
    assert tw["named_lines"] == 5
    assert tw["by"] == {"ExploreToward": 1, "continue": 1, "zombie": 1}


def _frame(seq, minute, parts):
    """A frame at game minute `minute` (me.hour), its parts {i: (bleeding, bandaged)}."""
    return {"seq": seq, "wallMs": 1000 * seq, "me": {"hour": minute / 60.0},
            "body": {"parts": [{"i": i, "bleeding": b, "bandaged": d} for i, (b, d) in parts.items()]}}


def test_dressed_reads_each_bleed_onset_to_its_parts_first_frame_not_bleeding_within_a_game_minute():
    """The rule: each false-to-true `bleeding` on a part is a wound (the first frame's bleeding parts too); it ends at
    the part's first later frame not bleeding (or not listed); dressed when that is within DRESS_MIN game minutes.
    Part 1 bleeds from the first frame and stops 0.5 min later (dressed); part 2 bleeds at 600.2 and stops at 602
    (1.8 min: not); part 2 bleeds again at 603 and never stops; part 3 bleeds at 601 and drops from the list at 601.9
    (0.9 min: ends, dressed by the rule)."""
    frames = [_frame(1, 600.0, {1: (True, False), 2: (False, False)}),
              _frame(2, 600.2, {1: (True, False), 2: (True, False)}),
              _frame(3, 600.5, {1: (False, True), 2: (True, False)}),
              _frame(4, 601.0, {1: (False, True), 2: (True, False), 3: (True, False)}),
              _frame(5, 601.9, {1: (False, True), 2: (True, False)}),
              _frame(6, 602.0, {1: (False, True), 2: (False, True)}),
              _frame(7, 603.0, {1: (False, True), 2: (True, True)}),
              _frame(8, 604.0, {1: (False, True), 2: (True, True)})]
    dr = TS.dressed(frames)
    assert [(r["part"], r["seq0"], r["seq1"]) for r in dr["rows"]] == [(1, 1, 3), (2, 2, 6), (3, 4, 5), (2, 7, None)]
    assert [None if r["minutes"] is None else round(r["minutes"], 3) for r in dr["rows"]] == [0.5, 1.8, 0.9, None]
    assert (dr["dressed"], dr["wounds"], dr["stopped"]) == (2, 4, 3)
    assert TS.dressed([]) == {"wounds": 0, "dressed": 0, "stopped": 0, "rows": []}


def test_dressed_holds_a_wound_ending_at_exactly_one_game_minute_off_the_frames_game_minute():
    """The bound is inclusive (review-t7 L1): a frame with no `me.hour` reads its whole `gameMin`, so a bleed from
    minute 600 to 601 is exactly DRESS_MIN and dressed; one from 601 to 603 is not."""
    frames = [{"seq": s, "wallMs": s, "gameMin": m, "body": {"parts": [{"i": i, "bleeding": b} for i, b in p]}}
              for s, m, p in ((1, 600, [(4, True)]), (2, 601, [(4, False), (5, True)]), (3, 603, [(5, False)]))]
    dr = TS.dressed(frames)
    assert [r["minutes"] for r in dr["rows"]] == [1.0, 2.0]
    assert (dr["dressed"], dr["wounds"]) == (1, 2)


def test_the_labels_are_loud_string_and_flee_retreat_an_unknown_word_marked_and_an_unresolved_target_counted():
    """Review-t7 M1: `string` (T's kite) and `flee` are retreat labels; every label seen prints in the detail's
    histogram, a word neither a retreat nor a KNOWN_LABELS word marked `?`; a play or intent target that resolves to
    neither a square nor a listed zombie is counted unresolved."""
    m = 1.0 / 60.0
    rows = [_line(10.0, play="string"), _line(10.0 + m, intent={"kind": "flee"}),
            _line(10.0 + 2 * m, play={"kind": "meet", "target": 99}), _line(10.0 + 3 * m, act="wander"),
            _line(10.0 + 4 * m, play={"kind": "travel", "target": [5, 5]}), _line(10.0 + 5 * m)]
    fl = TS.flee_minutes(rows)
    assert fl["lines"] == 2 and fl["by"] == {"string": 1, "flee": 1}
    assert TS.label_histogram(rows) == {"string": 1, "flee": 1, "meet": 1, "wander?": 1, "travel": 1}
    L = E._Lines({}, rows, [])
    assert TS.toward_minutes(L)["unresolved"] == 1
    s = {"hits": {}, "flee": fl, "toward": TS.toward_minutes(L), "dressed": TS.dressed([]),
         "melees": TS.melees_superseded({}, []), "goal_wait": None, "standing": None, "away": TS.away_minutes(L),
         "legs": TS.leg_minutes(rows), "labels": TS.label_histogram(rows), "kills_events": None,
         "kills_matched": None}
    d = "\n".join(TS.detail(s))
    assert "'wander?': 1" in d and "1 lines' play targets resolved to nothing" in d


def _fz(seq, me_x, zombies, wall=None):
    """A frame at seq (wallMs 1000 x seq unless given, me.hour 10 h plus seq minutes), the character at (me_x, 0),
    its zombies [(id, x, hasTarget)]."""
    return {"kind": "frame", "seq": seq, "wallMs": wall if wall is not None else 1000.0 * seq,
            "me": {"x": me_x, "y": 0.0, "hour": 10.0 + seq / 60.0},
            "zombies": [{"id": z, "x": x, "y": 0.0, "hasTarget": t} for z, x, t in zombies]}


def test_away_counts_the_frame_intervals_moving_off_the_nearest_chaser_with_no_refuge_named():
    """The rule (the controller's ruling on review-t7 M2): an interval counts its game minutes when the character
    moved, its first frame's nearest `hasTarget` zombie is listed on the second and farther by more than MOVE_EPS, and
    no line in force (the line at or before the first frame, and any written within) names a refuge. The intervals:
    1-2 away from chaser 7 (2 to 3 tiles: 1 min); 2-3 moved but 7 closes to 0.5; 3-4 standing while 7 steps off to
    1.0: no; 4-5 the untargeted 3 falls behind (1 to 2 tiles) while the chaser 7 closes to 0.5: no; 5-6 the chaser 7 not listed on the second; 6-7 away
    from 10 under a `filter_door` play (skipped); 7-8 away under a ladder line whose threat why's `shelter` is set
    (skipped); 8-9 away under a line naming none (1 min)."""
    fr = [_fz(1, 0.0, [(7, 2.0, True)]), _fz(2, -1.0, [(7, 2.0, True)]),
          _fz(3, -2.0, [(7, -1.5, True)]), _fz(4, -2.0, [(3, -1.0, False), (7, -1.0, True)]),
          _fz(5, -3.0, [(3, -1.0, False), (7, -3.5, True)]), _fz(6, -4.0, [(10, -6.0, True)]),
          _fz(7, -3.0, [(10, -6.0, True)]), _fz(8, -2.0, [(10, -6.0, True)]), _fz(9, -1.0, [(10, -6.0, True)])]
    rows = [dict(_line(10.0, play={"kind": "fight"}), wall=1.0),
            dict(_line(10.1, play={"kind": "filter_door"}), wall=6.0),
            dict(_line(10.12, threat={"shelter": 2}), wall=7.0),
            dict(_line(10.13), wall=8.0)]
    aw = TS.away_minutes(E._Lines({}, rows, fr))
    assert (aw["intervals"], aw["refuge_skipped"]) == (2, 2)
    assert aw["minutes"] == pytest.approx(2.0, abs=1e-6)
    assert TS.names_refuge(rows[1]) and TS.names_refuge(rows[2]) and not TS.names_refuge(rows[3])
    assert TS.names_refuge(_line(10.0, threat={"doorway_pick": "standing"}))
    assert not TS.names_refuge(_line(10.0, threat={"doorway_pick": "no_door"}))
    assert not TS.names_refuge(_line(10.0, threat={"leg": "enter"}))     # the melee stance's entry leg (R1)


def _act(aid, state, wall, step=None, reason=""):
    return {"kind": "act", "type": "melee", "aid": aid, "state": state, "reason": reason, "wallMs": wall,
            "result": {"step": step} if step else {}}


def test_melees_superseded_counts_a_superseded_span_with_no_press_step_over_the_melees_sent():
    """The rule: a span ending failed superseded with none of swing, shove, stomp or floor among its steps is
    superseded before its swing; one superseded after a swing, a floor swing, a lone stomp or a lone shove is not (the
    last three counted in `no_swing_step`; review-t7 L1: a press set missing the stomp or the shove fails here); a done
    span and one failed for another reason are neither; the denominator the record's melee actions (8 here, one never
    accepted), else the spans (7)."""
    lines = [_act("a1", "accepted", 1), _act("a1", "progress", 2, "face"), _act("a1", "failed", 3, None, "superseded"),
             _act("a2", "accepted", 4), _act("a2", "progress", 5, "swing"), _act("a2", "progress", 6, "back"),
             _act("a2", "failed", 7, None, "superseded"),
             _act("a3", "accepted", 8), _act("a3", "progress", 9, "floor"), _act("a3", "failed", 10, None, "superseded"),
             _act("a4", "accepted", 11), _act("a4", "progress", 12, "stand"), _act("a4", "done", 13),
             _act("a5", "accepted", 14), _act("a5", "failed", 15, None, "lost"),
             _act("a6", "accepted", 16), _act("a6", "progress", 17, "stomp"), _act("a6", "failed", 18, None, "superseded"),
             _act("a7", "accepted", 19), _act("a7", "progress", 20, "shove"), _act("a7", "failed", 21, None, "superseded")]
    out = {"loop": {"actions": [{"aid": "a%d" % i, "type": "melee"} for i in range(1, 9)] + [{"type": "walkTo"}]}}
    ml = TS.melees_superseded(out, lines)
    assert (ml["superseded_before"], ml["superseded"], ml["no_swing_step"], ml["sent"]) == (1, 5, 4, 8)
    assert ml["aids"] == ["a1"]
    assert TS.melees_superseded({}, lines)["sent"] == 7


# ================================================================ the end cell and the trial cells
@pytest.mark.parametrize("out, end", [
    ({"stop": {"reason": "death", "gameMin": 702}}, "death@702"), ({"stop": {"reason": "day_cap"}}, "cap"),
    ({"stop": {"reason": "client_end"}}, "crash"), ({"stop": {"reason": "bus_dead"}}, "crash"),
    ({"error": "boom"}, "crash"), ({"stop": {"reason": "memory"}}, "end"), ({"loop": {}}, "end"), ({}, "-")])
def test_the_end_cell_reads_the_stop(out, end):
    assert TS.end_cell(out) == end


def test_the_trial_cells_read_trial_json():
    t = {"variant": "doctrine", "switches": ["MEET", "FINISH"], "commit": "0123456789abcdef", "dirty": "feedbeefcafe",
         "fixture": "arena-east", "waves": "w2"}
    assert (TS._variant(t), TS._commit(t), TS._fixture(t)) == (
        "doctrine [MEET, FINISH]", "01234567-dirty-feedbeef", "arena-east / w2")
    t = dict(t, switches={}, dirty=False, waves=None)
    assert (TS._variant(t), TS._commit(t), TS._fixture(t)) == ("doctrine", "01234567", "arena-east")
    assert (TS._variant(None), TS._commit(None), TS._fixture(None)) == ("-", "-", "-")


# ================================================================ the log
def _write_run(root, health=90.0, trial=True, kill=False):
    """A run folder: trial.json, the record, a two-line decision log and a client state log with two frames (and a
    zombie_dead event when `kill`)."""
    os.makedirs(root)
    rid = os.path.basename(root)
    if trial:
        with open(os.path.join(root, TS.TRIAL_JSON), "w", encoding="utf-8") as fh:
            json.dump({"variant": "ladder", "switches": [], "commit": "abcdef0123", "dirty": False,
                       "fixture": "arena-east", "minutes": 5, "waves": None, "no_llm": True}, fh)
    with open(os.path.join(root, "x_trial.json"), "w", encoding="utf-8") as fh:
        json.dump({"run_id": rid, "stop": {"reason": "day_cap"}, "loop": {"first_game_min": 600, "game_min": 605,
                                                                        "actions": []}}, fh)
    with open(os.path.join(root, "decision.log"), "w", encoding="utf-8") as fh:
        for h in (10.0, 10.05):
            fh.write(json.dumps(_line(h, branch="threat", threat={"flee": "many"})) + "\n")
    sd = os.path.join(root, "clients", "admin", "Lua", "pzagent", "admin")
    os.makedirs(sd)
    with open(os.path.join(sd, "state.log"), "w", encoding="utf-8") as fh:
        for seq in (1, 2):
            fh.write(pza1.encode("frame", {"seq": seq, "tick": seq, "wallMs": 36000000 + seq, "gameMin": 600,
                                           "worldAge": 1.0, "me": {"x": 1.5, "y": 2.5, "z": 0, "hour": 10.0,
                                                                   "hitReaction": ""},
                                           "body": {"health": health, "parts": []}}) + "\n")
        if kill:
            fh.write(pza1.encode("event", {"seq": 3, "tick": 3, "wallMs": 36000003, "event": "zombie_dead",
                                           "id": 7}) + "\n")
    return root


@pytest.fixture
def log(tmp_path):
    p = str(tmp_path / "trials.md")
    shutil.copyfile(TRIALS, p)
    return p


def test_a_run_folder_scores_from_its_client_tree_and_its_trial_json(tmp_path):
    run = _write_run(str(tmp_path / "x_trial-20261106-101010"), kill=True)
    cs = TS.cells(TS.score(run))
    assert cs == ["x_trial-20261106-101010", "ladder", "abcdef01", "arena-east", "5", "1 (matched 0)", "0 / 0",
                  "0.00", "3.0 / 3.0 (away 0.0)", "0.0 / 3.0", "0 / 0", "0 / 0 (0 superseded)", "cap", "90", ""]


def test_dry_writes_nothing_and_a_run_appends_then_replaces_its_own_row_keeping_seen(tmp_path, log, capsys):
    run = _write_run(str(tmp_path / "x_trial-20261106-101010"))
    before = open(log, "rb").read()
    assert TS.main([run, "--dry", "--log", log, "--seen", "a"]) == 0
    assert open(log, "rb").read() == before
    assert "| x_trial-20261106-101010 | ladder |" in capsys.readouterr().out
    assert TS.main([run, "--log", log, "--seen", "saw one", "--seen", "saw two", "--seen", "saw | three"]) == 0
    _, rows = TS.read_log(log)
    assert len(rows) == 1 and TS.parse_row(rows[0])[-1] == "saw one / saw two / saw | three"
    assert TS.main([run, "--log", log]) == 0                       # rescored with no --seen: kept, not duplicated
    _, rows = TS.read_log(log)
    assert len(rows) == 1 and TS.parse_row(rows[0])[-1] == "saw one / saw two / saw | three"
    assert open(log, encoding="utf-8").read().startswith(open(TRIALS, encoding="utf-8").read().rstrip("\n"))


def test_rescore_all_rebuilds_each_row_keeping_seen_keeps_a_gone_folders_row_and_appends_a_new_one(tmp_path, log):
    runs = str(tmp_path / "runs")
    a = _write_run(os.path.join(runs, "x_trial-20261106-101010"), health=90.0)
    TS.main([a, "--log", log, "--seen", "kept text"])
    shutil.rmtree(a)
    _write_run(a, health=40.0)                                     # the scorer changed its reading: a new health
    gone = TS.format_row(["x_trial-20261101-000000"] + ["-"] * 13 + ["old seen"])
    with open(log, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(gone + "\n")
    _write_run(os.path.join(runs, "x_trial-20261107-000000"))
    _write_run(os.path.join(runs, "f_goals_99-20261107-000000"))  # not a trial: not read
    before = open(log, "rb").read()
    TS.rescore_all(log, runs, dry=True)
    assert open(log, "rb").read() == before
    assert TS.main(["--rescore-all", "--log", log, "--runs", runs]) == 0
    _, rows = TS.read_log(log)
    cells = [TS.parse_row(r) for r in rows]
    assert [c[0] for c in cells] == ["x_trial-20261106-101010", "x_trial-20261101-000000", "x_trial-20261107-000000"]
    assert (cells[0][13], cells[0][14]) == ("40", "kept text")
    assert rows[1] == gone
    assert cells[2][14] == ""


def test_the_command_line_refuses_what_it_does_not_define():
    """Statically, through the parser alone: an unknown flag, an abbreviation, no run, a run beside --rescore-all,
    --seen beside --rescore-all and a fourth --seen each exit 2 before any read."""
    for argv in (["r", "--bogus"], ["r", "--dr"], [], ["r", "--rescore-all"], ["--rescore-all", "--seen", "x"],
                 ["r", "--seen", "1", "--seen", "2", "--seen", "3", "--seen", "4"]):
        with pytest.raises(SystemExit) as e:
            TS.parse_args(argv)
        assert e.value.code == 2
    assert TS.main([os.path.join(REPO, "no-such-run"), "--dry"]) == 2
