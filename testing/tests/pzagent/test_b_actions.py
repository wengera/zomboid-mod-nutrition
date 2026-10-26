"""drivers/b_actions.py, drivers/b_grade.py, agent/reasons.py and grades.gate_b (Plan 21 Task 10), offline: the driver
is never invoked.

The sequence runs against a FakeMod that plays PZAgent's Lua into a tmp state dir with the real line shapes
(PZAgent_Main.lua and PZAgent_Sense.lua: hello {modVersion, build, user, rate, mode}; ack {cmdSeq, ok, reason}; frame
{x, y, z, items, hunger, thirst, gameMin, worldAge, goal {seq, name, state, detail}, cost}; scan {r, squares [{x, y, z,
solid, containers, floor, door?}], missing, scanMs, hour} with an empty table rendered as an object; event item_added
{fullType} on a frame tick when the inventory grew, naming its last item) on an injected clock."""
import json
import math
import os
import copy
import re
import types

import pytest

from agent import grades as G
from agent.drivers import b_actions as D
from agent.drivers import b_grade as BG
from agent.link import Link
from agent.reasons import DONE, REASONS

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ACT_LUA = os.path.join(REPO, "testing", "PZAgent", "PZAgent", "42", "media", "lua", "client", "PZAgent_Act.lua")
X = D.X


# ================================================================ static: refusal, constants, the closed reason set
def test_the_driver_refuses_arguments_before_main():
    with open(D.__file__, encoding="utf-8") as fh:
        src = fh.read()
    i_ref, i_main = src.index("refusal = parse_argv(sys.argv[1:], __file__)"), src.rindex("    main()")
    assert src.index('if __name__ == "__main__":') < i_ref < i_main
    assert "sys.exit(refusal)" in src[i_ref:i_main]
    assert D.parse_argv(["x"], D.__file__) and D.parse_argv(["--help"], D.__file__)
    assert "b_actions.py takes no arguments" in D.parse_argv(["x"], D.__file__)
    assert D.parse_argv([], D.__file__) is None


def test_the_constants_name_the_drivers_own_file_and_profile():
    assert os.path.basename(D.__file__) == D.DRIVER == D.KEY + ".py"
    assert D.KEY == "b_actions" and D.ARTIFACT == D.KEY + ".json"
    assert D.PROFILE == "testing/profiles/agent-nozombies.toml" and os.path.isfile(os.path.join(REPO, D.PROFILE))
    assert (D.BUDGET_S, D.USER, D.MIN_FREE_GB, D.SEQUENCES) == (560.0, "admin", 12.0, G.SEQUENCES)
    assert D.GOAL_TIMEOUT_S == 60.0 and D.EAT_POLL_S == 5.0 and D.EAT_POLL_MAX_S == 60.0
    assert dict(D.SPAWN) == {"Base.WaterBottle": D.SEQUENCES, "Base.Apple": D.SEQUENCES}
    assert D.EAT_HUNGER == 0.3 and not hasattr(D, "WATER_PREFIX_RX") and not hasattr(D, "water_like")


def act_src():
    with open(ACT_LUA, encoding="utf-8") as fh:
        return fh.read()


def test_reasons_equal_the_act_headers_reasons_line():
    lines = [ln for ln in act_src().splitlines() if ln.startswith("-- reasons:")]
    assert len(lines) == 1
    header = {r.strip() for r in lines[0][len("-- reasons:"):].split("|")}
    assert header == set(REASONS)


def test_every_failed_detail_the_act_file_sets_is_in_the_set():
    found = set(re.findall(r'(?:"failed",\s*|failWalk\(p, g, )"([^"]+)"', act_src()))
    assert found and found <= REASONS, found - REASONS


def test_done_equals_the_act_headers_done_line_and_every_done_detail_is_in_it():
    lines = [ln for ln in act_src().splitlines() if ln.startswith("-- done:")]
    assert len(lines) == 1
    header = {r.strip() for r in lines[0][len("-- done:"):].split("|")}
    assert header == set(DONE)
    found = set(re.findall(r'"done",\s*"([^"]+)"', act_src()))
    assert found == set(DONE), found ^ set(DONE)


def test_no_failed_pair_uses_a_done_detail_and_no_done_pair_a_failed_one():
    src = act_src()
    failed = set(re.findall(r'(?:"failed",\s*|failWalk\(p, g, )"([^"]+)"', src))
    done = set(re.findall(r'"done",\s*"([^"]+)"', src))
    assert not (failed & DONE) and not (done & REASONS) and not (DONE & REASONS)


# ================================================================ gate_b
SEEN = {"before": {"hunger": 0.3, "calories": 1000.0}, "after": [{"hunger": 0.3, "calories": 1000.0},
                                                                  {"hunger": 0.15, "calories": 1095.0}]}


def passing_out():
    rep = {"completed": True, "steps": [{"goal": "eat", "state": "done", "detail": "consumed"}], "server_eat": SEEN}
    return {"readings": {"reps": [copy.deepcopy(rep) for _ in range(5)]}}


def test_gate_b_passes_a_passing_set():
    g = G.gate_b(passing_out())
    assert g["verdict"] == "GO" and all(g["pass"].values()), g
    assert (g["sequences"], g["rows"], g["completed"], g["reasons_in_set"], g["eats_seen_by_server"]) == (
        5, 5, 5, True, 5)


def test_gate_b_four_of_five_completed_passes_three_does_not():
    o = passing_out()
    o["readings"]["reps"][0]["completed"] = False
    o["readings"]["reps"][0]["steps"].append({"goal": "loot", "state": "failed", "detail": "no match"})
    g = G.gate_b(o)
    assert g["pass"]["completed"] and g["verdict"] == "GO" and g["failing_steps"] == ["loot:no match"]
    o["readings"]["reps"][1]["completed"] = False
    g = G.gate_b(o)
    assert [k for k, v in g["pass"].items() if not v] == ["completed"] and g["verdict"] == "NO-GO"


def _cross(name):
    o = passing_out()
    reps = o["readings"]["reps"]
    if name == "completed":
        for r in reps[:2]:
            r["completed"] = False
    elif name == "reasons_in_set":
        reps[0]["steps"] = [{"goal": "open", "state": "failed", "detail": "door jammed"}]
    elif name == "eats_seen_by_server":
        reps[3]["server_eat"]["after"] = [{"hunger": 0.3, "calories": 1000.0}] * 12
        reps[3]["server_eat"]["moved"] = True                  # the driver's flag is never trusted: re-derived
    return o


@pytest.mark.parametrize("name", ["completed", "reasons_in_set", "eats_seen_by_server"])
def test_each_gate_crossed_alone_flips_it_and_the_verdict(name):
    g = G.gate_b(_cross(name))
    assert g["verdict"] == "NO-GO"
    assert [k for k, v in g["pass"].items() if not v] == [name]


@pytest.mark.parametrize("after,seen", [({"hunger": 0.0, "calories": 1095.0}, True),     # hunger clamped, kcal rose
                                        ({"hunger": 0.1, "calories": 1000.0}, True),     # hunger fell alone
                                        ({"hunger": 0.0, "calories": 1000.0}, False),
                                        ({"hunger": None, "calories": None}, False)])
def test_an_eat_is_seen_by_hunger_falling_or_calories_rising(after, seen):
    se = {"before": {"hunger": 0.0 if after["hunger"] == 0.0 else 0.3, "calories": 1000.0}, "after": [after]}
    o = passing_out()
    o["readings"]["reps"][0]["server_eat"] = se
    assert G.gate_b(o)["eats_seen_by_server"] == (5 if seen else 4)
    assert D.eat_seen(se["before"], after) is seen


def test_a_refused_or_timed_out_step_counts_against_completed_only():
    o = passing_out()
    o["readings"]["reps"][0]["steps"].append({"goal": "eat", "state": "timeout", "detail": "goal 9 not finished"})
    o["readings"]["reps"][1]["steps"].append({"goal": "eat", "state": "refused", "detail": "unknown goal"})
    assert G.gate_b(o)["reasons_in_set"] is True


ALL3 = {"completed", "reasons_in_set", "eats_seen_by_server"}


@pytest.mark.parametrize("drop", ["readings", "reps", "reps_empty", "completed_key", "server_eat", "before",
                                  "row_not_dict"])
def test_a_missing_reading_fails_its_gate(drop):
    o = passing_out()
    reps = o.get("readings", {}).get("reps")
    if drop == "readings":
        del o["readings"]
    elif drop == "reps":
        del o["readings"]["reps"]
    elif drop == "reps_empty":
        o["readings"]["reps"] = []
    elif drop == "completed_key":
        del reps[0]["completed"]                               # one row: four completed would otherwise pass
    elif drop == "server_eat":
        del reps[0]["server_eat"]
    elif drop == "before":
        reps[0]["server_eat"] = {"after": SEEN["after"]}
    elif drop == "row_not_dict":
        reps[2] = "rep 3"
    g = G.gate_b(o)
    assert g["verdict"] == "NO-GO" and g["sequences"] == G.SEQUENCES
    want = {"readings": ALL3, "reps": ALL3, "reps_empty": ALL3, "row_not_dict": ALL3, "completed_key": {"completed"},
            "server_eat": {"eats_seen_by_server"}, "before": {"eats_seen_by_server"}}[drop]
    assert {k for k, v in g["pass"].items() if not v} == want
    if drop in ("completed_key", "row_not_dict"):
        assert g["completed"] is None


def test_sequences_reports_the_target_and_rows_the_artifact():
    o = passing_out()
    o["readings"]["reps"] = o["readings"]["reps"][:3]
    g = G.gate_b(o)
    assert (g["sequences"], g["rows"], g["verdict"]) == (5, 3, "NO-GO")


def test_b_grade_exits_on_the_verdict_and_writes_strict_json(tmp_path, capsys):
    p = tmp_path / "b.json"
    p.write_text(json.dumps(passing_out()))
    assert BG.main([str(p)]) == 0
    assert json.loads(capsys.readouterr().out)["verdict"] == "GO"
    p.write_text(json.dumps(_cross("eats_seen_by_server")))
    assert BG.main([str(p)]) == 1
    assert BG.main([]) == 2 and BG.main([str(tmp_path / "none.json")]) == 2
    assert BG.finite({"a": math.inf, "b": [float("nan"), 1.5], "c": "x"}) == {"a": None, "b": [None, 1.5], "c": "x"}


# ================================================================ pure helpers
def test_line_cells_excludes_both_ends():
    assert D.line_cells(0, 0, 4, 0) == [(1, 0), (2, 0), (3, 0)]
    assert D.line_cells(0, 0, 3, 3) == [(1, 1), (2, 2)]
    assert D.line_cells(5, 5, 5, 5) == [] and D.line_cells(0, 0, 1, 0) == []
    assert D.line_cells(4, 2, 0, 0)[0] in ((3, 2), (3, 1)) and len(D.line_cells(4, 2, 0, 0)) == 3


def sq(x, y, **kw):
    s = {"x": x, "y": y, "z": 0, "solid": False, "containers": {}, "floor": {}}
    s.update(kw)
    return s


def test_pick_prefers_the_tier_then_the_distance_and_skips_picked_and_empty_containers():
    scan = {"squares": [sq(1, 0, containers=[{"type": "crate", "n": 0, "items": {}}]),
                        sq(3, 0, containers=[{"type": "fridge", "n": 2, "items": ["Base.Apple", "Base.WaterBottle"]}]),
                        sq(2, 0, containers=[{"type": "shelf", "n": 1, "items": ["Base.Hammer"]}]),
                        sq(0, 1)]}
    p = D.pick_container(scan, 0.5, 0.5)
    assert (p["x"], p["tier"], p["items"]) == (3, 3, 2)
    assert D.pick_container(scan, 0.5, 0.5, exclude={(3, 0, 0)})["x"] == 2
    assert D.pick_container(scan, 0.5, 0.5, exclude={(3, 0, 0), (2, 0, 0)})["x"] == 1
    assert D.pick_container({"squares": [sq(0, 1)]}, 0.5, 0.5) is None
    assert D.pick_container({"squares": {}}, 0.5, 0.5) is None                    # an empty scan renders as {}


def test_door_between_and_beside():
    shut, ajar = {"open": False, "locked": False, "barricaded": False}, {"open": True, "locked": False,
                                                                          "barricaded": False}
    scan = {"squares": [sq(x, y) for x in range(0, 6) for y in range(-1, 2)]}
    by = D.by_xy(scan)
    by[(2, 0)]["window"] = shut
    pick = {"x": 5, "y": 0, "z": 0}
    assert D.door_between(scan, 0.5, 0.5, pick) == {"x": 2, "y": 0, "kind": "window", "open": False}
    by[(2, 0)].pop("window")
    by[(1, 0)]["door"] = ajar
    assert D.door_between(scan, 0.5, 0.5, pick) == {"x": 1, "y": 0, "kind": "door", "open": True}
    by[(1, 0)].pop("door")
    assert D.door_between(scan, 0.5, 0.5, pick) is None
    by[(4, 0)]["solid"] = True
    assert D.beside(scan, 0.5, 0.5, pick) in ((4, -1), (4, 1))
    for xy in ((4, -1), (4, 1), (5, -1), (5, 1)):
        by[xy]["solid"] = True
    assert D.beside(scan, 0.5, 0.5, pick) is None                                 # x = 6 lies outside the scan


def test_eat_choice_takes_only_edible_food_ids():
    assert D.eat_choice(["Base.WaterBottle", "Base.Pop", "Base.Wine", "Base.Whiskey", "Base.Bread"]) == (
        "Base.Bread", "looted")
    assert D.eat_choice(["Base.Watermelon", "Base.TinnedBeans", "Base.Hammer"]) == ("Base.Apple", "fallback")
    assert D.eat_choice([]) == ("Base.Apple", "fallback")
    ids = D.food_ids()
    assert "Base.Apple" in ids and "Base.Wine" not in ids and "Base.WaterBottle" not in ids
    assert "Base.WaterBottleFull" not in ids


def test_the_water_bottle_is_water_like_and_names_that_merely_start_with_water_are_not():
    assert D.WATER_RX.search("Base.WaterBottle")
    assert D.tier(sq(0, 0, containers=[{"items": ["Base.WaterBottle"]}])) == 2
    assert D.tier(sq(0, 0, containers=[{"items": ["Base.WaterPurificationTablets"]}])) == 1


def test_body_reading_reads_the_nutrition_get_reply():
    assert D.body_reading({"ack": {"hunger": 0.25, "calories": 1200.5}, "wallMs": 7}) == {
        "hunger": 0.25, "calories": 1200.5, "wallMs": 7}
    assert D.body_reading({"ack": "no online player admin"}) == {"hunger": None, "calories": None, "wallMs": None}
    assert D.body_reading({"ack": {"hunger": True}})["hunger"] is None and D.body_reading(None)["calories"] is None


# ================================================================ pre-boot, on the real profile and a real run layout
def stub_checks(monkeypatch, dirty=False, lint=(), tracked=""):
    monkeypatch.setattr(D.DL.C, "doctor", lambda: (True, "ok"))
    monkeypatch.setattr(D.DL.harness, "lint_paths", lambda srcs: list(lint))
    monkeypatch.setattr(D.DL.C, "git_dirty", lambda rel: (dirty, ""))
    real = D.DL.C.git_say
    monkeypatch.setattr(D.DL.C, "git_say", lambda *a: tracked if a[0] == "ls-files" else real(*a))


def test_preboot_on_the_real_profile(agent_fixture, monkeypatch):
    stub_checks(monkeypatch)
    pre, ok = D.preboot(D.__file__)
    assert ok, pre
    assert pre["profile"] == "agent-nozombies" and pre["lint_errors"] == [] and pre["doctor_clean"]
    assert pre["driver_checks"] == {"driver_file": True, "driver_prefix": True, "profile_exists": True,
                                    "no_committed_artifact": True, "agent_lua_dirty": False, "driver_dirty": False}


def test_preboot_refuses(agent_fixture, monkeypatch):
    stub_checks(monkeypatch, tracked="testing/artifacts/b_actions-20261026-120000/b_actions.json")
    pre, ok = D.preboot(D.__file__)
    assert not ok and pre["driver_checks"]["no_committed_artifact"] is False
    stub_checks(monkeypatch, dirty=True)
    assert D.preboot(D.__file__)[1] is False
    stub_checks(monkeypatch, lint=["ERROR x"])
    assert D.preboot(D.__file__)[1] is False
    stub_checks(monkeypatch)
    pre, ok = D.preboot(os.path.join(os.path.dirname(D.__file__), "a_pipe.py"))
    assert not ok and pre["driver_checks"]["driver_file"] is False


def test_main_clears_the_state_dir_through_the_boot_seam_and_gates_memory_before_the_boot():
    src = open(D.__file__, encoding="utf-8").read()
    assert "make_client=clearing_make_client(session.make_client)" in src
    assert "session.make_client =" not in src
    i_x, i_g, i_b = src.index("xs = X.Xs("), src.index("memory_gate(xs)"), src.index("DL.boot(")
    assert i_x < i_g < i_b
    assert "act = Actions(xs, DL.link_for(clients, USER))" in src and 'out["finished"] = True' in src


def test_the_memory_wait_never_eats_the_budget():
    c = Clock()
    xs = X.Xs(D.new_out(), node=lambda s: s, clock=c.now, budget_s=560.0)

    def wait(gb):
        c.t += 1500.0
        return True, [{"wall": c.t, "free_gb": gb}]
    D.memory_gate(xs, wait=wait)
    assert xs.wall() == 0 and xs.out["memory_wait"][0]["free_gb"] == 12.0
    xs2 = X.Xs(D.new_out(), node=lambda s: s, clock=c.now)
    with pytest.raises(SystemExit):
        D.memory_gate(xs2, wait=lambda gb: (False, [{"wall": 0, "free_gb": 3.0}]))
    assert xs2.out["error"] == "blocked: memory"


# ================================================================ the sequence against a FakeMod
class Clock:
    def __init__(self):
        self.t = 1_790_000_000.0

    def now(self):
        return self.t


SHUT = {"open": False, "locked": False, "barricaded": False}
FRIDGE = [{"type": "fridge", "n": 2, "items": ["Base.Apple", "Base.WaterBottle"]}]
APPLE_TIMER = 2080.0          # healthFromFoodTimer an apple adds (FOOD_EATEN level 2)
REFUSE_TIMER = 3200.0         # FOOD_EATEN level 3: the eat and the drink refuse to start


class FakeMod:
    """PZAgent's Lua and the server's body for Stage B, one tick at a time on `clock`. The spawn is (100.5, 200.5); a
    scan shows a line of shut doors at x = 102 and five fridges at (105, 200..204); every goal ends after GOAL_TICKS.
    The body: Hunger starts low (0.05) and rises only while the food timer is 0; an apple lowers Hunger by 0.15 to a
    floor of 0, adds 95 calories and APPLE_TIMER; at a timer of REFUSE_TIMER or more the eat and the drink fail "not
    valid". `fail` maps a step label (goto, open, loot food, loot water, eat, drink) to the detail it fails with;
    `blind` keeps the server's reading still; `hunger_blind` keeps only its hunger still; `no_containers` scans none; a scan
    is acked "queued" and emitted as scanPart lines (test_a_pipe_3's FakeMod3 shapes), `drop_parts` part numbers never
    emitted."""
    TPS = 60
    GOAL_TICKS = 20
    FRAME_EVERY = 12
    RISE = 0.00005
    PART_SQUARES = 60

    def __init__(self, d, clock, fail=None, blind=False, hunger_blind=False, no_containers=False, drop_parts=()):
        os.makedirs(d, exist_ok=True)
        self.d, self.clock = d, clock
        self.fail, self.blind, self.hunger_blind, self.no_containers = dict(fail or {}), blind, hunger_blind, \
            no_containers
        self.seq = self.tick = self.last_cmd = 0
        self.buf = []
        self.x, self.y = 100.5, 200.5
        self.hunger, self.thirst, self.calories, self.timer = 0.05, 0.2, 1000.0, 0.0
        self.inv, self.prev_items = [], 0
        self.goal = None
        self.ready = False
        self.cmds = []
        self.log = []                 # ("cmd", label) and ("write", cmd) in the order they reached the game
        self.scan_id, self.job, self.drop_parts = 10, None, set(drop_parts)

    def emit(self, kind, body):
        self.seq += 1
        body.update(kind=kind, seq=self.seq, tick=self.tick, wallMs=int(self.clock.t * 1000))
        self.buf.append(json.dumps(body))

    def flush(self):
        if self.buf:
            with open(os.path.join(self.d, "state.log"), "a", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(self.buf) + "\n")
            self.buf = []

    def poll(self):
        p = os.path.join(self.d, "cmd.txt")
        if not os.path.isfile(p):
            return None
        kv = dict(ln.split("=", 1) for ln in open(p, encoding="utf-8").read().splitlines() if "=" in ln)
        seq = int(kv["seq"])
        if seq <= self.last_cmd:
            return None
        self.last_cmd = seq
        return {"seq": seq, "goal": kv.get("goal", ""), "args": kv.get("args", "")}

    def square(self, x, y):
        s = {"x": x, "y": y, "z": 0, "solid": False, "solidTrans": False, "light": 1.0, "containers": {},
             "floor": {}}
        if x == 102:
            s["door"] = dict(SHUT)
        if x == 105 and 200 <= y <= 204 and not self.no_containers:
            s["containers"] = json.loads(json.dumps(FRIDGE))
            s["room"], s["building"] = "kitchen", 7
        return s

    def scan(self, r):
        """Pass 3's Lua: the grid is fixed at the start under the next scanId (a running scan is replaced); its
        squares go out as scanPart lines of at most PART_SQUARES, one per tick from the ack's own tick."""
        px, py = math.floor(self.x), math.floor(self.y)
        sqs = [self.square(px + dx, py + dy) for dy in range(-r, r + 1) for dx in range(-r, r + 1)]
        self.scan_id += 1
        self.job = {"id": self.scan_id, "r": r, "squares": sqs, "parts": math.ceil(len(sqs) / self.PART_SQUARES),
                    "next": 1}

    def scan_part(self):
        j = self.job
        k, n, m = j["next"], j["parts"], self.PART_SQUARES
        body = {"scanId": j["id"], "r": j["r"], "hour": 7, "part": k, "parts": n,
                "squares": j["squares"][(k - 1) * m:k * m], "missing": {}, "stepMs": 1, "emitMs": 2 if k > 1 else 0}
        if k == n:
            body.update(done=True, scanMs=n, scanTicks=n, scanMsPerTick=[1] * n, scanStepMaxMs=1)
            self.job = None
        else:
            j["next"] = k + 1
        if k not in self.drop_parts:
            self.emit("scanPart", body)
        self.flush()

    def label(self, goal, a):
        return goal + (" " + a[2] if goal == "loot" and len(a) > 2 else "")

    def end(self, g):
        lab = self.label(g["name"], g["argv"])
        if lab in self.fail:
            g["state"], g["detail"] = "failed", self.fail[lab]
            return
        a = g["argv"]
        if g["name"] in ("eat", "drink") and self.timer >= REFUSE_TIMER:
            g["state"], g["detail"] = "failed", "not valid"
            return
        if g["name"] == "goto":
            self.x, self.y = float(a[0]), float(a[1])
            g["detail"] = "d=0.1"
        elif g["name"] == "open":
            g["detail"] = "open"
        elif lab == "loot food":
            self.inv.append("Base.Apple")
            g["detail"] = "moved=1"
        elif lab == "loot water":
            self.inv.append("Base.WaterBottle")
            g["detail"] = "moved=1"
        elif g["name"] == "eat":
            if a[0] not in self.inv:
                g["state"], g["detail"] = "failed", "none held"
                return
            self.inv.remove(a[0])
            self.hunger = max(0.0, self.hunger - 0.15)
            self.calories += 95.0
            self.timer += APPLE_TIMER
            g["detail"] = "consumed"
        elif g["name"] == "drink":
            self.thirst = max(0.0, self.thirst - 0.1)
            g["detail"] = "consumed"
        g["state"] = "done"

    def status(self):
        g = self.goal
        if g is None:
            return {"seq": 0, "name": "idle", "state": "idle", "detail": ""}
        if g["state"] != "running":
            g["reported"] = True
        return {"seq": g["seq"], "name": g["name"], "state": g["state"], "detail": g["detail"]}

    def step(self):
        self.clock.t += 1.0 / self.TPS
        self.tick += 1
        if self.timer <= 0:
            self.hunger = min(1.0, self.hunger + self.RISE)
        cmd = self.poll()
        if cmd:
            self.cmds.append(cmd)
            a = cmd["args"].split()
            self.log.append(("cmd", self.label(cmd["goal"], a)))
            if cmd["goal"] == "scan":
                self.scan(int(a[0]))
            else:
                self.goal = {"seq": cmd["seq"], "name": cmd["goal"], "argv": a, "state": "running", "detail": "",
                             "ticks": 0}
            self.emit("ack", {"cmdSeq": cmd["seq"], "ok": True, "reason": "queued" if cmd["goal"] == "scan" else ""})
            self.flush()
        if self.job is not None:
            self.scan_part()
        if not self.ready:
            self.emit("hello", {"modVersion": "0.1", "build": "42.21.0", "user": "admin", "rate": 5,
                                "mode": "append"})
            self.flush()
            self.ready = True
        g = self.goal
        if g is not None:
            if g["state"] != "running":
                if g.get("reported"):
                    self.goal = None
            else:
                g["ticks"] += 1
                if g["ticks"] >= self.GOAL_TICKS:
                    self.end(g)
        if self.tick % self.FRAME_EVERY == 0:
            gm = 420 + self.tick // 60
            if len(self.inv) > self.prev_items:
                self.emit("event", {"event": "item_added", "fullType": self.inv[-1], "gameMin": gm,
                                    "worldAge": 31.5})
            self.prev_items = len(self.inv)
            self.emit("frame", {"x": self.x, "y": self.y, "z": 0, "items": len(self.inv), "hunger": self.hunger,
                                "thirst": self.thirst, "gameMin": gm, "worldAge": 31.5, "goal": self.status(),
                                "zombies": {}, "cost": {"pollMs": 0.1, "actMs": 0.1, "senseMs": 0.2,
                                                        "linkMs": 0.0, "dropped": 0}})
            self.flush()

    def sleep(self, dt):
        for _ in range(max(1, round(dt * self.TPS))):
            self.step()

    # ---- the server's side of the bus (the real reply shapes: PZTestKit_Server.lua's @reply lines)
    def snapshot(self):
        return {"calories": self.calories, "carbs": 100.0, "lipids": 50.0, "proteins": 60.0, "weight": 80.0,
                "hunger": self.hunger, "thirst": self.thirst, "statsApi": True, "incWeight": False,
                "incWeightLot": False, "decWeight": False}

    def write(self, xs, tag, cmd, args):
        self.sleep(0.05)
        self.log.append(("write", cmd))
        a = args.split()
        if cmd == "foodtimer.set":
            before = self.timer
            self.timer = float(a[1])
            return {"requested": float(a[1]), "before": before, "set": True, "after": self.timer}
        if cmd == "stats.set" and a[1] == "hunger":
            self.hunger = float(a[2])
            snap = self.snapshot()
            snap["applied"] = {"hunger": "stats"}
            return snap
        return "usage"

    def read(self, xs, user):
        self.sleep(0.05)
        snap = self.snapshot()
        if self.blind:
            snap["hunger"], snap["calories"] = 0.3, 1000.0
        elif self.hunger_blind:
            snap["hunger"] = 0.3
        return {"ack": snap, "wallMs": self.clock.t * 1000}


def run_actions(tmp_path, budget_s=1e9, no_reset=False, **flags):
    clock = Clock()
    sd = str(tmp_path / "clients" / "admin" / "Lua" / "pzagent" / "admin")
    mod = FakeMod(sd, clock, **flags)
    out = D.new_out()
    spawns, reads = [], []

    def spawn(ft, n, tag):
        spawns.append((ft, n, tag))
        mod.inv.extend([ft] * n)
        return {"type": ft, "n": n, "confirmed": True}

    def body(xs, user):
        reads.append(user)
        return mod.read(xs, user)

    def write(xs, tag, cmd, args):
        return "skipped" if no_reset else mod.write(xs, tag, cmd, args)

    xs = X.Xs(out, node=lambda side: side, clock=clock.now, sleep=mod.sleep, budget_s=budget_s, user="admin")
    xs.path = str(tmp_path / D.ARTIFACT)
    act = D.Actions(xs, Link(sd, clock=clock.now), clock=clock.now, sleep=mod.sleep, body=body, write=write,
                    spawn=spawn)
    if no_reset:
        act.eat_reset = lambda row: None                     # today's driver before fix 1: no reset before the eat
    act.run()
    out["client_lua_errors"] = 0
    return out, mod, spawns, reads


def labels(cmds):
    out = []
    for c in cmds:
        a = c["args"].split()
        out.append(c["goal"] + (" " + a[2] if c["goal"] == "loot" else ""))
    return out


def test_the_sequence_runs_every_step_in_order_on_a_correct_mod(tmp_path):
    out, mod, spawns, reads = run_actions(tmp_path)
    assert out["phase_errors"] == {} and "budget_stop" not in out, out["phase_errors"]
    rd = out["readings"]
    assert rd["spawn_xy"]["x"] == 100.5 and rd["spawn_xy"]["y"] == 200.5
    assert spawns == [("Base.WaterBottle", 5, "spawn_WaterBottle"), ("Base.Apple", 5, "spawn_Apple")]
    assert [s["type"] for s in rd["spawned"]] == ["Base.WaterBottle", "Base.Apple"]
    assert labels(mod.cmds) == list(D.STEP_ORDER) * 5
    reps = rd["reps"]
    assert len(reps) == 5 and all(r["completed"] for r in reps)
    assert [r["pick"]["y"] for r in reps] == [200, 201, 202, 203, 204]       # each repetition a fresh container
    for i, r in enumerate(reps):
        assert r["pick"]["x"] == 105 and r["pick"]["tier"] == 3
        assert r["door"] == {"x": 102, "y": r["door"]["y"], "kind": "door", "open": False}
        steps = r["steps"]
        assert [s["goal"] for s in steps] == ["scan", "open", "goto", "loot", "loot", "eat", "drink", "goto"]
        assert steps[1]["args"] == "102 %d" % r["door"]["y"]
        assert steps[2]["args"].startswith("104.5 ")
        assert steps[3]["args"] == "105 %d food" % r["pick"]["y"] and steps[4]["args"].endswith(" water")
        assert steps[5]["args"] == "Base.Apple" and r["eat_pick"]["from"] == "looted"
        assert r["eat_pick"]["added"][0] == "Base.Apple"                     # the loot's own item, not the spawn's
        assert steps[7]["args"] == "100.5 200.5"
        for s in steps:
            assert s["state"] == "done" and s["ms"] > 0 and isinstance(s["seq"], int)
        for s in steps[1:]:
            assert s["ack"]["ok"] is True and s["gameMin"] >= 420 and s["worldAge"] == 31.5
        assert [s["detail"] for s in steps[3:7]] == ["moved=1", "moved=1", "consumed", "consumed"]
        se = r["server_eat"]
        assert se["moved"] is True and len(se["after"]) == 1
        assert se["before"]["hunger"] == pytest.approx(0.3, abs=0.01) and se["before"]["calories"] == 1000.0 + 95.0 * i
        assert se["after"][0]["hunger"] < se["before"]["hunger"] and se["after"][0]["calories"] > se["before"][
            "calories"]
        assert se["after"][0]["wallMs"] - se["before"]["wallMs"] >= D.EAT_POLL_S * 1000
        assert "hunger" in se["client_before"] and "hunger" in se["client_after"]      # informational, may predate the write
        assert [(w["cmd"], w["args"]) for w in se["resets"]] == [("foodtimer.set", "admin 0"),
                                                                  ("stats.set", "admin hunger 0.3")]
        assert se["resets"][0]["reply"]["after"] == 0.0 and se["resets"][1]["reply"]["hunger"] == 0.3
    assert reads == ["admin"] * 10
    writes = out["world_changes"]["writes"]
    assert len(writes) == 10 and [w["rep"] for w in writes] == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
    ev = [e for e in mod.log if e[0] == "write" or e[1] in ("loot water", "eat")]
    assert ev == [("cmd", "loot water"), ("write", "foodtimer.set"), ("write", "stats.set"), ("cmd", "eat")] * 5
    assert out["gaps"] == [] and out["bad"] == 0 and out["lua_errors"] == 0 and out["missing"] == []
    g = G.gate_b(out)
    assert g["verdict"] == "GO" and g["completed"] == 5 and g["eats_seen_by_server"] == 5, g
    persisted = json.loads((tmp_path / D.ARTIFACT).read_text(encoding="utf-8"))
    assert len(persisted["readings"]["reps"]) == 5 and persisted["readings"]["reps"][4]["completed"] is True


def test_a_failed_step_records_its_detail_and_the_sequence_goes_on(tmp_path):
    out, mod, _, _ = run_actions(tmp_path, fail={"loot water": "no match"})
    assert labels(mod.cmds) == list(D.STEP_ORDER) * 5
    for r in out["readings"]["reps"]:
        lw = r["steps"][4]
        assert (lw["goal"], lw["args"].split()[-1], lw["state"], lw["detail"]) == ("loot", "water", "failed",
                                                                                   "no match")
        assert r["completed"] is False and r["steps"][5]["state"] == "done"
    g = G.gate_b(out)
    assert g["completed"] == 0 and g["reasons_in_set"] is True and g["eats_seen_by_server"] == 5
    assert [k for k, v in g["pass"].items() if not v] == ["completed"] and g["failing_steps"] == ["loot:no match"]


def test_a_detail_outside_the_closed_set_fails_reasons_in_set(tmp_path):
    out, _, _, _ = run_actions(tmp_path, fail={"open": "door jammed"})
    g = G.gate_b(out)
    assert g["reasons_in_set"] is False and g["reasons_outside_set"] == ["door jammed"] and g["verdict"] == "NO-GO"


def test_a_failed_food_loot_eats_the_spawned_fallback(tmp_path):
    out, mod, _, _ = run_actions(tmp_path, fail={"loot food": "empty"})
    for r in out["readings"]["reps"]:
        assert r["eat_pick"] == {"fullType": "Base.Apple", "from": "fallback", "added": ["Base.WaterBottle"]}
        assert r["steps"][5]["state"] == "done" and r["server_eat"]["moved"] is True
    assert mod.inv.count("Base.Apple") == 0                                  # the five spawned apples, all eaten


def test_a_server_that_never_sees_the_eat_polls_out_its_window(tmp_path):
    out, _, _, reads = run_actions(tmp_path, blind=True)
    n = int(D.EAT_POLL_MAX_S / D.EAT_POLL_S)
    for r in out["readings"]["reps"]:
        se = r["server_eat"]
        assert se["moved"] is False and len(se["after"]) == n and all(a["hunger"] == 0.3 for a in se["after"])
    assert len(reads) == 5 * (n + 1)
    g = G.gate_b(out)
    assert g["eats_seen_by_server"] == 0 and [k for k, v in g["pass"].items() if not v] == ["eats_seen_by_server"]


def test_a_failed_eat_is_not_polled(tmp_path):
    out, _, _, reads = run_actions(tmp_path, fail={"eat": "interrupted"})
    for r in out["readings"]["reps"]:
        assert r["server_eat"]["skipped"] == "eat failed" and r["server_eat"]["after"] == []
    assert len(reads) == 5                                                   # the pre-eat reading only


def test_without_the_reset_a_full_food_timer_refuses_the_later_eats(tmp_path):
    """The defect fix 1 closes, reproduced: no foodtimer/hunger write before the eat. Hunger clamps at 0 after the
    first apple and stays there under the timer, from the second eat the timer refuses the drink and from the third the eat."""
    out, _, _, _ = run_actions(tmp_path, no_reset=True)
    reps = out["readings"]["reps"]
    assert 0.05 < reps[0]["server_eat"]["before"]["hunger"] < 0.15
    assert reps[1]["server_eat"]["before"]["hunger"] == 0.0
    assert [r["steps"][5]["detail"] for r in reps[2:]] == ["not valid"] * 3
    assert [r["steps"][6]["detail"] for r in reps[1:]] == ["not valid"] * 4      # the second apple tips the drink
    g = G.gate_b(out)
    assert g["eats_seen_by_server"] == 2 and g["completed"] == 1 and g["verdict"] == "NO-GO"


def test_calories_alone_show_the_eat_when_the_hunger_reading_holds_still(tmp_path):
    out, _, _, _ = run_actions(tmp_path, hunger_blind=True)
    for r in out["readings"]["reps"]:
        se = r["server_eat"]
        assert se["moved"] is True and se["after"][-1]["hunger"] == se["before"]["hunger"] == 0.3
        assert se["after"][-1]["calories"] > se["before"]["calories"]
    assert G.gate_b(out)["eats_seen_by_server"] == 5


def test_no_container_scans_wide_once_and_stops_the_repetition(tmp_path):
    out, mod, _, _ = run_actions(tmp_path, no_containers=True)
    assert [c["args"] for c in mod.cmds] == ["15", "25"] * 5 and labels(mod.cmds) == ["scan"] * 10
    for r in out["readings"]["reps"]:
        assert r["notes"] == ["no_container_in_scan", "no_container_in_wide_scan"] and r["completed"] is False
        assert [s["state"] for s in r["steps"]] == ["done", "done"] and r["pick"] is None
    assert G.gate_b(out)["completed"] == 0


def test_the_budget_stops_the_repetitions_and_keeps_the_partial_row(tmp_path):
    out, _, _, _ = run_actions(tmp_path, budget_s=40.0)
    assert "budget_stop" in out and out["budget_stop"]["phase"].startswith("rep")
    reps = out["readings"]["reps"]
    assert reps and reps[-1]["completed"] is False
    persisted = json.loads((tmp_path / D.ARTIFACT).read_text(encoding="utf-8"))
    assert len(persisted["readings"]["reps"]) == len(reps)
    assert G.gate_b(out)["verdict"] == "NO-GO"


def test_a_silent_link_fails_every_phase_with_no_hello(tmp_path):
    clock = Clock()
    sd = str(tmp_path / "sd")
    xs = X.Xs(D.new_out(), node=lambda side: side, clock=clock.now, sleep=lambda dt: setattr(clock, "t", clock.t + dt),
              user="admin")
    act = D.Actions(xs, Link(sd, clock=clock.now), clock=clock.now,
                    sleep=lambda dt: setattr(clock, "t", clock.t + dt), spawn=lambda *a: types.SimpleNamespace())
    act.run()
    pe = xs.out["phase_errors"]
    assert "no hello" in pe["hello"]["error"] and all("no hello" in pe["rep%d" % i]["error"] for i in range(1, 6))
    assert xs.out["readings"]["reps"] == [] and G.gate_b(xs.out)["verdict"] == "NO-GO"


def test_the_scan_step_awaits_the_done_part_and_unions_the_parts(tmp_path):
    out, mod, _, _ = run_actions(tmp_path)
    n15 = math.ceil(31 * 31 / FakeMod.PART_SQUARES)
    for i, r in enumerate(out["readings"]["reps"]):
        sc = r["scan"][0]
        assert (sc["r"], sc["scanId"], sc["parts"], sc["partsSeen"], sc["squares"]) == (15, 11 + i, n15, n15, 31 * 31)
        assert sc["scanTicks"] == n15 and sc["missing"] == []
        st = r["steps"][0]
        assert st["ack"]["reason"] == "queued" and st["detail"] == "squares=961 parts=%d/%d" % (n15, n15)
    with open(os.path.join(mod.d, "state.log"), encoding="utf-8") as fh:
        kinds = {json.loads(ln)["kind"] for ln in fh if ln.strip()}
    assert "scanPart" in kinds and "scan" not in kinds                      # no whole-scan line any more


def test_a_scan_whose_done_part_never_comes_times_out_within_its_window(tmp_path):
    n15 = math.ceil(31 * 31 / FakeMod.PART_SQUARES)
    out, mod, _, _ = run_actions(tmp_path, drop_parts={n15, math.ceil(51 * 51 / FakeMod.PART_SQUARES)})
    for r in out["readings"]["reps"]:
        s15, s25 = r["steps"][0], r["steps"][1]
        assert s15["state"] == "timeout" and s15["detail"].startswith("no done part")
        assert D.SCAN_TIMEOUT_S * 1000 <= s15["ms"] <= (D.SCAN_TIMEOUT_S + 1) * 1000
        assert s25["args"] == "25" and s25["state"] == "timeout" and r["pick"] is None
        assert r["notes"] == ["no_container_in_scan", "no_container_in_wide_scan"]


def test_a_gappy_scan_still_unions_the_parts_that_came(tmp_path):
    out, _, _, _ = run_actions(tmp_path, drop_parts={2})
    n15 = math.ceil(31 * 31 / FakeMod.PART_SQUARES)
    for r in out["readings"]["reps"]:
        sc = r["scan"][0]
        assert sc["partsSeen"] == n15 - 1 and sc["squares"] == 31 * 31 - FakeMod.PART_SQUARES
        assert r["completed"] is True                                         # the fridges lie outside part 2
