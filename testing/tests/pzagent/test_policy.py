"""agent/policy.py (Plan 21 Task 11): every branch from a World built of synthetic lines, the sent-only-when-changed
rule, and a replayed death log reproducing its last ten decisions on an injected clock."""
import json
import os

import pytest

from agent import policy as P
from agent.world import World

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
DEATH = os.path.join(FIX, "log-synthetic-death.log")
DEATH_TAIL = os.path.join(FIX, "log-synthetic-death.decisions.jsonl")


class FakeLink:
    def __init__(self):
        self.cmds = []

    def send(self, goal, args=""):
        self.cmds.append((goal, args))
        return len(self.cmds)


def frame(wall=1000, x=100.0, y=100.0, zombies=(), goal=None, **me):
    line = {"kind": "frame", "seq": 1, "tick": 1, "wallMs": wall, "gameMin": me.pop("gameMin", 600), "worldAge": 1.0,
            "x": x, "y": y, "z": 0, "health": 100.0, "hunger": 0.2, "thirst": 0.2, "fatigue": 0.1,
            "zombies": list(zombies) or {}}
    line.update(me)
    if goal is not None:
        line["goal"] = goal
    return line


def zombie(zid, x, y):
    return {"id": zid, "x": x, "y": y, "dist": 0.0, "hasTarget": True, "crawler": False}


def sq(x, y, **k):
    return dict({"x": x, "y": y, "z": 0, "solid": False, "containers": [], "floor": []}, **k)


def scan(squares):
    return {"kind": "scan", "seq": 2, "tick": 2, "wallMs": 0, "r": 3, "squares": squares, "missing": []}


def event(name, **k):
    return dict({"kind": "event", "seq": 3, "tick": 3, "wallMs": 0, "event": name}, **k)


def make(tmp_path, *lines):
    w = World()
    for ln in lines:
        w.apply(ln)
    link = FakeLink()
    t = {"now": 0.0}
    pol = P.Policy(w, link, str(tmp_path / "decision.log"), lambda: t["now"])
    return w, link, pol


def decisions(tmp_path):
    with open(tmp_path / "decision.log", encoding="utf-8") as f:
        return [json.loads(ln) for ln in f]


BAT = {"type": "Base.BaseballBat", "condition": 10}


# ================================================================ threat
def test_threat_fights_when_armed_and_at_most_two_within_danger_r(tmp_path):
    w, link, pol = make(tmp_path, frame(zombies=[zombie(1, 104.0, 100.0), zombie(2, 100.0, 105.0)], weapon=BAT))
    assert pol.tick() == "fight" and link.cmds == [("fight", "")]
    d = decisions(tmp_path)[-1]
    assert d["branch"] == "threat" and d["inputs"]["threats"] == 2 and d["inputs"]["armed"] is True


def test_threat_ignores_a_zombie_beyond_danger_r(tmp_path):
    w, link, pol = make(tmp_path, frame(zombies=[zombie(1, 106.5, 100.0)], weapon=BAT))
    pol.tick()
    assert decisions(tmp_path)[-1]["branch"] != "threat"


@pytest.mark.parametrize("why", ["unarmed", "broken", "three", "low health"])
def test_threat_flees_to_the_farthest_known_walkable_square(tmp_path, why):
    zs = [zombie(1, 103.0, 100.0), zombie(2, 103.0, 101.0)]
    me = {"weapon": BAT}
    if why == "unarmed":
        me = {}
    if why == "broken":
        me = {"weapon": {"type": "Base.BaseballBat", "condition": 0}}
    if why == "three":
        zs.append(zombie(3, 104.0, 100.0))
    if why == "low health":
        me["health"] = 39.0
    w, link, pol = make(tmp_path, scan([sq(95, 100), sq(80, 100, solid=True), sq(110, 100)]), frame(zombies=zs, **me))
    assert pol.tick() == "flee" and link.cmds == [("flee", "95 100")]


def test_threat_flee_without_a_map_runs_flee_dist_away(tmp_path):
    w, link, pol = make(tmp_path, frame(zombies=[zombie(1, 100.0, 103.0)]))
    pol.tick()
    assert link.cmds == [("flee", "100 92")]


# ================================================================ need
def test_need_drinks_when_thirsty_and_eats_a_held_food(tmp_path):
    w, link, pol = make(tmp_path, frame(thirst=0.6))
    assert pol.tick() == "drink"
    w, link, pol = make(tmp_path, event("item_added", fullType="Base.Apple"), frame(hunger=0.6))
    assert pol.tick() == "eat" and link.cmds == [("eat", "Base.Apple")]
    assert decisions(tmp_path)[-1]["branch"] == "need"


def test_need_marks_food_and_falls_through_to_forage_for_it(tmp_path):
    w, link, pol = make(tmp_path, scan([sq(101, 100, containers=[{"type": "crate", "n": 1, "items": ["Base.Nails"]}]),
                                        sq(103, 100, containers=[{"type": "fridge", "n": 1, "items": ["Base.Apple"]}])]),
                        frame(hunger=0.6))
    assert pol.tick() == "loot" and link.cmds == [("loot", "103 100 food")]
    d = decisions(tmp_path)[-1]
    assert d["branch"] == "forage" and d["inputs"]["need"] == "food"


def test_need_eat_and_drink_track_what_the_events_say_is_held(tmp_path):
    w, link, pol = make(tmp_path, event("item_added", fullType="Base.Apple"), frame(hunger=0.6))
    pol.tick()                                               # eat Base.Apple, seq 1
    w.apply(event("goal_done", goalSeq=1))
    w.apply(frame(wall=2000, hunger=0.6, thirst=0.6))
    assert pol.tick() == "drink"                             # the apple is gone; drinking is worth a try
    w.apply(event("goal_failed", goalSeq=2, reason="none held"))
    w.apply(frame(wall=3000, hunger=0.6, thirst=0.6))
    pol.tick()                                               # no drink held: water is marked, nothing to forage
    d = decisions(tmp_path)[-1]
    assert d["inputs"]["need"] == "water" and d["goal"] == "scan" and link.cmds.count(("drink", "")) == 1
    w.apply(event("item_added", fullType="Base.WaterBottle"))
    w.apply(frame(wall=4000, hunger=0.6, thirst=0.6))
    assert pol.tick() != "drink"                             # the failed drink still cools
    for _ in range(P.FAILED_COOLDOWN_TICKS - 2):
        pol.tick()
    assert pol.tick() == "drink"                             # cooled: the water is worth a try


# ================================================================ sleep
def test_sleep_at_night_when_tired_walks_indoors_then_sleeps(tmp_path):
    w, link, pol = make(tmp_path, scan([sq(105, 100, room="bedroom", building=3), sq(101, 100)]),
                        frame(fatigue=0.8, gameMin=23 * 60))
    assert pol.tick() == "goto" and link.cmds == [("goto", "105 100")]
    w.apply(frame(wall=2000, x=105.0, y=100.0, fatigue=0.8, gameMin=23 * 60,
                  goal={"seq": 1, "name": "goto", "state": "done", "detail": "d=0"}))
    assert pol.tick() == "sleep" and decisions(tmp_path)[-1]["branch"] == "sleep"


@pytest.mark.parametrize("fatigue, gm", [(0.7, 23 * 60), (0.8, 12 * 60)])
def test_sleep_needs_both_fatigue_over_t_and_night(tmp_path, fatigue, gm):
    w, link, pol = make(tmp_path, scan([sq(100, 100, room="bedroom")]), frame(fatigue=fatigue, gameMin=gm))
    pol.tick()
    assert decisions(tmp_path)[-1]["branch"] != "sleep"


def test_sleep_where_standing_when_no_indoor_square_is_known(tmp_path):
    w, link, pol = make(tmp_path, frame(fatigue=0.9, gameMin=2 * 60))
    assert pol.tick() == "sleep"


# ================================================================ forage
def test_forage_loots_the_nearest_unlooted_and_marks_it_when_the_loot_ends(tmp_path):
    crate = {"type": "crate", "n": 1, "items": ["Base.Nails"]}
    w, link, pol = make(tmp_path, scan([sq(102, 100, containers=[crate]), sq(106, 100, containers=[crate])]), frame())
    assert pol.tick() == "loot" and link.cmds == [("loot", "102 100 all")]
    w.apply(event("goal_failed", goalSeq=1, reason="not adjacent"))
    w.apply(frame(wall=2000))
    assert pol.tick() == "loot" and link.cmds[-1] == ("loot", "106 100 all")
    assert w.containers[(102, 100, 0, 0)]["looted"] is True


# ================================================================ explore
def test_explore_scans_first_then_walks_to_the_edge_then_scans_there(tmp_path):
    w, link, pol = make(tmp_path, frame())
    assert pol.tick() == "scan" and link.cmds == [("scan", "10")]
    w.apply(scan([sq(x, y) for x in range(99, 102) for y in range(99, 102)]))
    w.apply(frame(wall=2000))
    assert pol.tick() == "goto" and link.cmds[-1] == ("goto", "99 100")
    w.apply(frame(wall=3000, goal={"seq": 2, "name": "goto", "state": "running", "detail": ""}))
    assert pol.tick() is None                                # still walking: the same goto is not re-sent
    w.apply(frame(wall=4000, x=99.0, goal={"seq": 2, "name": "goto", "state": "done", "detail": "d=0"}))
    assert pol.tick() == "scan" and decisions(tmp_path)[-1]["branch"] == "explore"


def test_nothing_to_do_logs_a_none_branch(tmp_path):
    w, link, pol = make(tmp_path, frame())
    pol.scanned.add(None)
    assert pol.tick() is None
    d = decisions(tmp_path)[-1]
    assert d["branch"] is None and d["goal"] is None and d["sent"] is False


# ================================================================ sent only when changed
def test_a_goal_is_sent_only_when_it_differs_from_the_running_one(tmp_path):
    zs = [zombie(1, 103.0, 100.0)]
    w, link, pol = make(tmp_path, frame(zombies=zs, weapon=BAT))
    assert pol.tick() == "fight"
    w.apply(frame(wall=2000, zombies=zs, weapon=BAT, goal={"seq": 1, "name": "fight", "state": "running", "detail": ""}))
    assert pol.tick() is None and link.cmds == [("fight", "")]
    assert decisions(tmp_path)[-1]["sent"] is False and decisions(tmp_path)[-1]["goal"] == "fight"
    w.apply(frame(wall=3000, zombies=zs, weapon=BAT, health=30.0,
                  goal={"seq": 1, "name": "fight", "state": "running", "detail": ""}))
    assert pol.tick() == "flee"                              # a different goal pre-empts the running one
    w.apply(frame(wall=4000, x=99.0, zombies=zs, weapon=BAT, health=30.0,
                  goal={"seq": 2, "name": "flee", "state": "running", "detail": ""}))
    assert pol.tick() is None                                # a flee's target moving is not a change
    w.apply(event("goal_failed", goalSeq=2, reason="cornered"))
    w.apply(frame(wall=5000, x=99.0, zombies=zs, health=30.0))
    assert pol.tick() == "flee" and link.cmds[-1] == ("flee", "91 100")   # a finished goal, new args: sent


def test_a_failed_goal_cools_for_ten_planner_ticks(tmp_path):
    zs = [zombie(1, 103.0, 100.0)]
    w, link, pol = make(tmp_path, frame(zombies=zs, health=30.0))
    pol.scanned.add(None)                                    # nothing else to do: explore has no edge
    assert pol.tick() == "flee" and link.cmds == [("flee", "92 100")]
    w.apply(event("goal_failed", goalSeq=1, reason="cornered"))
    for i in range(P.FAILED_COOLDOWN_TICKS):
        w.apply(frame(wall=2000 + i, zombies=zs, health=30.0))
        assert pol.tick() is None, i                         # the same flee is not re-sent while it cools
    d = decisions(tmp_path)[-1]
    assert d["inputs"]["cooled"] == ["flee", "92 100"] and d["branch"] is None
    w.apply(frame(wall=3000, zombies=zs, health=30.0))
    assert pol.tick() == "flee" and link.cmds == [("flee", "92 100")] * 2
    assert decisions(tmp_path)[-1]["inputs"]["cooled"] is None


def test_a_cooled_goal_passes_over_to_the_next_branch(tmp_path):
    crate = {"type": "crate", "n": 1, "items": ["Base.Nails"]}
    w, link, pol = make(tmp_path, scan([sq(102, 100, containers=[crate])]), frame(thirst=0.6))
    assert pol.tick() == "drink"
    w.apply(event("goal_failed", goalSeq=1, reason="not valid"))
    w.apply(frame(wall=2000, thirst=0.6))
    assert pol.tick() == "loot" and decisions(tmp_path)[-1]["inputs"]["cooled"] == ["drink", ""]


def test_each_branch_logs_its_own_inputs(tmp_path):
    crate = {"type": "crate", "n": 1, "items": ["Base.Apple"]}
    w, link, pol = make(tmp_path, scan([sq(103, 100, containers=[crate])]), frame(hunger=0.6))
    pol.tick()
    d = decisions(tmp_path)[-1]
    b = d["inputs"]["branches"]
    assert d["branch"] == "forage" and b["forage"] == {"container": [103, 100, 0, 0]}
    assert b["need"] == {"food": [], "waterOk": True} and d["inputs"]["need"] == "food"
    assert b["threat"] == {} and b["sleep"] == {} and "explore" not in b      # explore was never tried


def test_args_change_re_sends_a_goto(tmp_path):
    w, link, pol = make(tmp_path, scan([sq(105, 100, room="r")]), frame(fatigue=0.9, gameMin=0))
    pol.tick()
    w.apply(scan([sq(102, 100, room="r")]))
    w.apply(frame(wall=2000, fatigue=0.9, gameMin=0, goal={"seq": 1, "name": "goto", "state": "running", "detail": ""}))
    assert pol.tick() == "goto" and link.cmds[-1] == ("goto", "102 100")


def test_decision_log_line_shape(tmp_path):
    w, link, pol = make(tmp_path, frame(gameMin=777))
    pol.clock = lambda: 12.5
    pol.tick()
    d = decisions(tmp_path)[-1]
    assert set(d) == {"wall", "gameMin", "branch", "inputs", "goal", "args", "sent"}
    assert d["wall"] == 12.5 and d["gameMin"] == 777
    assert set(d["inputs"]) == {"x", "y", "health", "hunger", "thirst", "fatigue", "armed", "threats", "nearest",
                                "running", "need", "cooled", "branches"}


def test_branch_order_is_the_specs():
    assert P.BRANCHES == ("threat", "need", "sleep", "forage", "explore")
    assert (P.DANGER_R, P.THIRST_T, P.HUNGER_T, P.FATIGUE_T) == (6.0, 0.5, 0.5, 0.7)


# ================================================================ a replayed death
def replay_decisions(tmp_path, name):
    """Plays the death log into a World, ticking the policy after each frame on the frame's own wall clock."""
    w = World()
    link = FakeLink()
    t = {"now": 0.0}
    log = tmp_path / name
    pol = P.Policy(w, link, str(log), lambda: t["now"])
    with open(DEATH, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            line = json.loads(ln)
            w.apply(line)
            if line["kind"] == "frame":
                t["now"] = line["wallMs"] / 1000.0
                pol.tick()
    with open(log, encoding="utf-8") as f:
        return f.read().splitlines(), link.cmds


def test_the_death_log_reproduces_its_last_ten_decisions(tmp_path):
    a, cmds = replay_decisions(tmp_path, "a.log")
    b, _ = replay_decisions(tmp_path, "b.log")
    assert a == b                                            # deterministic, byte for byte
    with open(DEATH_TAIL, encoding="utf-8") as f:
        golden = f.read().splitlines()
    assert len(golden) == 10 and a[-10:] == golden
    last = [json.loads(ln) for ln in a[-10:]]
    assert last[-1]["inputs"]["health"] == 0.0               # the log ends on the death
    assert cmds[-2:] == [("fight", ""), ("flee", "92 100")]  # the fight failed low health; the bot fled
    assert [d["goal"] for d in last[-3:]] == ["flee", "flee", "flee"] and not any(d["sent"] for d in last[-2:])


def test_the_death_log_has_sixty_lines_and_its_frames_carry_the_sent_seqs(tmp_path):
    with open(DEATH, encoding="utf-8") as f:
        lines = [json.loads(ln) for ln in f if ln.strip()]
    assert len(lines) == 60
    _, cmds = replay_decisions(tmp_path, "c.log")
    seqs = {ln["goal"]["seq"] for ln in lines if ln["kind"] == "frame" and ln.get("goal")}
    assert seqs <= set(range(1, len(cmds) + 1))
