"""drivers/b_actions_2.py (Plan 21b Stage B pass 2), offline: the driver is never invoked. The sequence runs against
test_b_actions's FakeMod (PZAgent's Lua and the server's body, the real line shapes) and subclasses of it whose
squares hold the containers each case needs."""
import json
import math
import os

from agent import grades as G
from agent.drivers import b_actions as BA
from agent.drivers import b_actions_2 as D
from agent.link import Link
from . import test_b_actions as T1

REPO = T1.REPO
X = D.X


# ================================================================ static: refusal, constants
def test_the_driver_refuses_arguments_before_main():
    with open(D.__file__, encoding="utf-8") as fh:
        src = fh.read()
    i_ref, i_main = src.index("refusal = parse_argv(sys.argv[1:], __file__)"), src.rindex("    main()")
    assert src.index('if __name__ == "__main__":') < i_ref < i_main
    assert "sys.exit(refusal)" in src[i_ref:i_main]
    assert D.parse_argv(["x"], D.__file__) and D.parse_argv(["--help"], D.__file__)
    assert "b_actions_2.py takes no arguments" in D.parse_argv(["x"], D.__file__)
    assert D.parse_argv([], D.__file__) is None


def test_the_constants_name_the_drivers_own_file_and_profile():
    assert os.path.basename(D.__file__) == D.DRIVER == D.KEY + ".py"
    assert D.KEY == "b_actions_2" and D.ARTIFACT == D.KEY + ".json"
    assert D.PROFILE == "testing/profiles/agent-nozombies.toml" and os.path.isfile(os.path.join(REPO, D.PROFILE))
    assert D.PASS1_RUN == "b_actions-20261026-183143" and D.new_out()["pass1_run"] == D.PASS1_RUN
    assert BA.SCAN_R_WIDE == 25 and BA.SCAN_R == 15 and D.STEP_ORDER == BA.STEP_ORDER
    assert D.CONSTANTS["PASS1_RUN"] == D.PASS1_RUN and D.CONSTANTS["WATER_RX"] == BA.WATER_RX.pattern
    assert D.CONSTANTS["DRINKWARE_RX"] == D.DRINKWARE_RX.pattern and D.CONSTANTS["NEVER_WATER_RX"] == r"\.Bleach\b"
    json.dumps(D.CONSTANTS)                                                    # the artifact carries it
    assert D.CONSTANTS["inherited_from_b_actions"] == BA.CONSTANTS
    assert (D.USER, D.MIN_FREE_GB, D.BUDGET_S) == (BA.USER, BA.MIN_FREE_GB, BA.BUDGET_S)
    assert D.Actions2.__mro__[1] is BA.Actions


def test_the_pass1_driver_is_imported_not_copied():
    src = open(D.__file__, encoding="utf-8").read()
    assert "from agent.drivers import b_actions as BA" in src
    assert "def eat_reset" not in src and "def eat_watch" not in src and "def scan(" not in src
    assert "act = Actions2(xs, DL.link_for(clients, USER))" in src and 'out["finished"] = True' in src
    assert "make_client=BA.clearing_make_client(session.make_client)" in src
    i_x, i_g, i_b = src.index("xs = X.Xs("), src.index("BA.memory_gate(xs)"), src.index("DL.boot(")
    assert i_x < i_g < i_b


# ================================================================ beside_free
sq = T1.sq


def grid(x0, x1, y0, y1):
    return {"squares": [sq(x, y, solidTrans=False) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]}


def test_beside_skips_a_solidtrans_neighbour_and_takes_the_next_nearest():
    scan = grid(0, 6, -1, 1)
    by = BA.by_xy(scan)
    pick = {"x": 5, "y": 0, "z": 0}
    assert D.beside_free(scan, 0.5, 0.5, pick) == (4, 0)
    by[(4, 0)]["solidTrans"] = True
    assert D.beside_free(scan, 0.5, 0.5, pick) in ((4, -1), (4, 1))
    assert BA.beside(scan, 0.5, 0.5, pick) == (4, 0)                           # pass 1 walked into it


def test_beside_skips_a_container_square_and_returns_none_when_none_is_free():
    scan = grid(0, 5, -1, 1)
    by = BA.by_xy(scan)
    pick = {"x": 5, "y": 0, "z": 0}
    by[(4, 0)]["containers"] = [{"type": "stove", "n": 0, "items": {}}]        # solid false, solidTrans false
    assert D.beside_free(scan, 0.5, 0.5, pick) in ((4, -1), (4, 1))
    by[(4, -1)]["solid"] = True
    by[(4, 1)]["solidTrans"] = True
    by[(5, -1)]["containers"] = [{"type": "counter", "n": 1, "items": ["Base.Fork"]}]
    assert D.beside_free(scan, 0.5, 0.5, pick) == (5, 1)
    by[(5, 1)]["solidTrans"] = True
    assert D.beside_free(scan, 0.5, 0.5, pick) is None                         # x = 6 lies outside the scan
    assert D.free_square({"x": 0, "y": 0, "containers": {}}) and not D.free_square(None)


def test_beside_on_pass1s_rep5_squares_never_picks_the_stove():
    """Pass 1's scanId 1 squares around rep 5's pick (10999,9696), copied from its state.log: pass 1 chose the stove
    square 10998,9697 (solid false, solidTrans true, a stove container) and the walk ended `stuck`."""
    def s(x, y, solid=False, st=False, cont=None):
        return {"x": x, "y": y, "z": 0, "solid": solid, "solidTrans": st, "containers": cont or {}}
    scan = {"squares": [s(10998, 9695), s(10999, 9695), s(11000, 9695),
                        s(10998, 9696, st=True, cont=[{"items": ["Base.DishCloth"], "n": 1, "type": "counter"}]),
                        s(10999, 9696, st=True, cont=[{"items": ["Base.Fork"], "n": 1, "type": "counter"}]),
                        s(11000, 9696, st=True, cont=[{"items": ["Base.Bandaid"], "n": 1, "type": "counter"}]),
                        s(10998, 9697, st=True, cont=[{"items": {}, "n": 0, "type": "stove"}]),
                        s(10999, 9697),
                        s(11000, 9697, st=True, cont=[{"items": {}, "n": 0, "type": "fridge"}])]}
    pick = {"x": 10999, "y": 9696, "z": 0}
    assert BA.beside(scan, 10997.5, 9699.5, pick) == (10998, 9697)
    assert D.beside_free(scan, 10997.5, 9699.5, pick) == (10999, 9697)


# ================================================================ the two picks
def box(x, y, items):
    return sq(x, y, containers=[{"type": "crate", "n": len(items), "items": list(items) if items else {}}])


def test_water_like_takes_the_regex_and_drinkware_and_never_bleach():
    for ft in ("Base.WaterBottle", "Base.Pop", "Base.DrinkingGlass", "Base.Mugl", "Base.MugRed", "Base.MugWhite",
               "Base.MugSpiffo", "Base.Kettle"):
        assert D.water_like(ft), ft
    for ft in ("Base.Bleach", "Base.WaterPurificationTablets", "Base.Oatmeal", "Base.Mug_Copper_Coffee",
               "Base.DrinkingGlassBroken"):
        assert not D.water_like(ft), ft
    assert not BA.WATER_RX.search("Base.DrinkingGlass")                        # pass 1's regex missed the house's glass


def test_matched_splits_the_items_by_the_food_dataset_and_water_like():
    s = sq(0, 0, containers=[{"items": ["Base.Oatmeal", "Base.Dogfood", "Base.Bleach"]},
                             {"items": ["Base.DrinkingGlass", "Base.Oatmeal", "Base.Fork"]}])
    assert D.matched(s) == (["Base.Oatmeal", "Base.Oatmeal"], ["Base.DrinkingGlass"])
    assert D.matched(box(0, 0, [])) == ([], [])


def test_a_food_pick_ranks_by_food_items_and_a_water_pick_by_water_items_nearest_within_the_rank():
    scan = {"squares": [box(1, 0, ["Base.Hammer"]),
                        box(2, 0, ["Base.DrinkingGlass"]),
                        box(3, 0, ["Base.Bread"]),
                        box(4, 0, ["Base.Bleach", "Base.Bleach"]),
                        box(7, 0, ["Base.Apple", "Base.Hammer", "Base.WaterBottle", "Base.Apple"]),
                        box(6, 0, ["Base.Apple", "Base.Mugl"]),
                        sq(0, 1)]}
    f, w = D.pick_kind(scan, 0.5, 0.5, "food"), D.pick_kind(scan, 0.5, 0.5, "water")
    assert (f["x"], f["tier"], f["items"], f["food"], f["water"]) == (6, 2, 2, ["Base.Apple"], ["Base.Mugl"])
    assert D.same_square(f, w) and w["tier"] == 2
    ex = {(6, 0, 0)}
    f = D.pick_kind(scan, 0.5, 0.5, "food", ex)
    assert (f["x"], f["tier"], f["food"], f["water"]) == (7, 2, ["Base.Apple", "Base.Apple"], ["Base.WaterBottle"])
    ex = {(6, 0, 0), (7, 0, 0)}
    f, w = D.pick_kind(scan, 0.5, 0.5, "food", ex), D.pick_kind(scan, 0.5, 0.5, "water", ex)
    assert (f["x"], f["tier"], f["food"], f["water"]) == (3, 1, ["Base.Bread"], [])
    assert (w["x"], w["tier"], w["food"], w["water"]) == (2, 1, [], ["Base.DrinkingGlass"])   # never the bleach
    assert not D.same_square(f, w) and not D.same_square(f, None)
    ex |= {(2, 0, 0), (3, 0, 0)}
    assert D.pick_kind(scan, 0.5, 0.5, "food", ex) is None and D.pick_kind(scan, 0.5, 0.5, "water", ex) is None
    near = {"squares": [box(1, 0, ["Base.Bread"]), box(9, 0, ["Base.Bread"])]}
    assert D.pick_kind(near, 8.5, 0.5, "food")["x"] == 9                      # nearest the player within the rank
    assert D.pick_kind({"squares": {}}, 0.5, 0.5, "food") is None and D.pick_kind(None, 0.5, 0.5, "water") is None
    assert D.has_container(scan) and not D.has_container({"squares": [sq(0, 0)]}) and not D.has_container(None)


def test_pass1s_house_gives_two_picks_the_oatmeal_and_the_glass():
    """The four candidate squares of pass 1's scanId 1 (its GUIDE's table), copied from its state.log."""
    def c(x, y, typ, items):
        return sq(x, y, solidTrans=True, containers=[{"type": typ, "n": len(items), "items": items}])
    scan = {"squares": [c(10998, 9698, "microwave", ["Base.Oatmeal"]),
                        c(10999, 9696, "counter", ["Base.Fork", "Base.Ladle", "Base.DrinkingGlass"]),
                        c(11000, 9696, "counter", ["Base.Bandaid", "Base.Dogfood", "Base.Thimble"]),
                        c(11000, 9701, "counter", ["Base.Bleach", "Base.Bleach", "Base.Soap2"])]}
    f, w = D.pick_kind(scan, 10997.5, 9699.5, "food"), D.pick_kind(scan, 10997.5, 9699.5, "water")
    assert (f["x"], f["y"], f["tier"], f["food"]) == (10998, 9698, 1, ["Base.Oatmeal"])
    assert (w["x"], w["y"], w["tier"], w["water"]) == (10999, 9696, 1, ["Base.DrinkingGlass"])
    assert BA.pick_container(scan, 10997.5, 9699.5)["tier"] == 1                # pass 1: every tier 1


# ================================================================ pre-boot
def test_preboot_on_the_real_profile(agent_fixture, monkeypatch):
    T1.stub_checks(monkeypatch)
    pre, ok = D.preboot(D.__file__)
    assert ok, pre
    assert pre["profile"] == "agent-nozombies" and pre["lint_errors"] == [] and pre["doctor_clean"]
    assert pre["driver_checks"] == {"driver_file": True, "driver_prefix": True, "profile_exists": True,
                                    "no_committed_artifact": True, "agent_lua_dirty": False,
                                    "pass1_driver_dirty": False, "driver_dirty": False}


def test_preboot_refuses(agent_fixture, monkeypatch):
    T1.stub_checks(monkeypatch, tracked="testing/artifacts/b_actions_2-20261027-120000/b_actions_2.json")
    pre, ok = D.preboot(D.__file__)
    assert not ok and pre["driver_checks"]["no_committed_artifact"] is False
    T1.stub_checks(monkeypatch, dirty=True)
    assert D.preboot(D.__file__)[1] is False
    T1.stub_checks(monkeypatch)
    pre, ok = D.preboot(os.path.join(os.path.dirname(D.__file__), "b_actions.py"))
    assert not ok and pre["driver_checks"]["driver_file"] is False


def test_driver_checks_refuse_a_dirty_pass1_driver_alone(tmp_path):
    def dirty(rel):
        return (rel == D.PASS1_DRIVER, "")
    c, ok = D.driver_checks(D.__file__, git_say=lambda *a: "", git_dirty=dirty)
    assert not ok and c["pass1_driver_dirty"] is True and c["agent_lua_dirty"] is False and c["driver_dirty"] is False
    c, ok = D.driver_checks(D.__file__, git_say=lambda *a: "", git_dirty=lambda rel: (False, ""))
    assert ok

# ================================================================ the sequence against a FakeMod
class Stocked(T1.FakeMod):
    """Pass 1's FakeMod: five fridges with an apple and a water bottle at (105, 200..204), doors at x = 102."""


class Boxes(T1.FakeMod):
    """Pass 1's FakeMod with its fridges replaced by BOXES {x: items} at y = 200..204 (doors at x = 102 kept)."""
    BOXES = {}

    def square(self, x, y):
        s = super().square(x, y)
        if 200 <= y <= 204:
            if x == 105:
                s["containers"] = {}
            if x in self.BOXES:
                s["containers"] = [{"type": "counter", "n": len(self.BOXES[x]), "items": list(self.BOXES[x])}]
        return s


class Split(Boxes):
    """Bread at x = 105 and a drinking glass at x = 108: two picks, both inside r = 15."""
    BOXES = {105: ["Base.Bread"], 108: ["Base.DrinkingGlass"]}


class WaterFar(Boxes):
    """Bread at x = 105, bleach at x = 110 (never water), a drinking glass at x = 118 (past r = 15, inside r = 25)."""
    BOXES = {105: ["Base.Bread"], 110: ["Base.Bleach"], 118: ["Base.DrinkingGlass"]}


class NoWater(Boxes):
    """Bread at x = 105 and bleach at x = 110: no water pick in either scan."""
    BOXES = {105: ["Base.Bread"], 110: ["Base.Bleach"]}


def run2(tmp_path, mod_cls=Stocked, budget_s=1e9, **flags):
    clock = T1.Clock()
    sd = str(tmp_path / "clients" / "admin" / "Lua" / "pzagent" / "admin")
    mod = mod_cls(sd, clock, **flags)
    out = D.new_out()

    def spawn(ft, n, tag):
        mod.inv.extend([ft] * n)
        return {"type": ft, "n": n, "confirmed": True}

    xs = X.Xs(out, node=lambda side: side, clock=clock.now, sleep=mod.sleep, budget_s=budget_s, user="admin")
    xs.path = str(tmp_path / D.ARTIFACT)
    act = D.Actions2(xs, Link(sd, clock=clock.now), clock=clock.now, sleep=mod.sleep, body=mod.read, write=mod.write,
                     spawn=spawn)
    act.run()
    out["client_lua_errors"] = 0
    return out, mod


def scans(mod):
    return [c["args"] for c in mod.cmds if c["goal"] == "scan"]


def test_a_stocked_container_completes_every_repetition_with_one_walk(tmp_path):
    out, mod = run2(tmp_path)
    assert out["phase_errors"] == {} and "budget_stop" not in out, out["phase_errors"]
    assert T1.labels(mod.cmds) == list(D.STEP_ORDER) * 5
    reps = out["readings"]["reps"]
    assert len(reps) == 5 and all(r["completed"] for r in reps)
    for i, r in enumerate(reps):
        assert "pick" not in r and "door" not in r
        assert r["notes"] == ["one_square_for_both_picks"] and r["scan"][0]["r"] == 15 and len(r["scan"]) == 1
        pf, pw = r["pick_food"], r["pick_water"]
        assert (pf["x"], pf["y"], pf["tier"]) == (105, 200 + i, 2) and D.same_square(pf, pw)
        assert pf["food"] == ["Base.Apple"] and pw["water"] == ["Base.WaterBottle"]
        assert r["door_food"]["x"] == 102 and r["door_water"] is None
        assert r["steps"][2]["args"].startswith("104.5 ")                       # (105,201) carries a fridge
        assert r["eat_pick"]["from"] == "looted" and r["server_eat"]["moved"] is True
    g = G.gate_b(out)
    assert g["verdict"] == "GO" and g["completed"] == 5 and g["eats_seen_by_server"] == 5, g
    persisted = json.loads((tmp_path / D.ARTIFACT).read_text(encoding="utf-8"))
    assert persisted["pass1_run"] == D.PASS1_RUN and persisted["readings"]["reps"][0]["completed"] is True


def test_two_picks_walk_to_each_and_loot_each(tmp_path):
    out, mod = run2(tmp_path, Split)
    assert scans(mod) == ["15"] * 5
    want = ["scan", "open", "goto", "loot food", "goto", "loot water", "eat", "drink", "goto"]
    assert T1.labels(mod.cmds) == want * 5                     # no door between x = 105 and x = 108: no second open
    for i, r in enumerate(out["readings"]["reps"]):
        pf, pw = r["pick_food"], r["pick_water"]
        assert (pf["x"], pf["y"], pf["food"], pw["x"], pw["y"], pw["water"]) == (
            105, 200 + i, ["Base.Bread"], 108, 200 + i, ["Base.DrinkingGlass"])
        st = r["steps"]
        assert st[3]["args"] == "105 %d food" % (200 + i) and st[5]["args"] == "108 %d water" % (200 + i)
        assert st[4]["args"].startswith("107.5 ")                              # beside the glass, from the bread
        assert r["door_food"]["x"] == 102 and r["door_water"] is None and r["notes"] == []
        assert r["completed"] is True
    assert G.gate_b(out)["verdict"] == "GO"


def test_a_pick_missing_from_the_near_scan_sends_the_wide_scan_and_bleach_is_never_water(tmp_path):
    out, mod = run2(tmp_path, WaterFar)
    assert scans(mod) == ["15", "25"] * 5
    for i, r in enumerate(out["readings"]["reps"]):
        assert r["notes"] == ["no_stocked_container_in_scan"] and [s["r"] for s in r["scan"]] == [15, 25]
        assert (r["pick_food"]["x"], r["pick_water"]["x"]) == (105, 118)
        assert r["pick_water"]["water"] == ["Base.DrinkingGlass"] and r["completed"] is True
    assert G.gate_b(out)["verdict"] == "GO"


def test_both_picks_near_do_not_send_the_wide_scan(tmp_path):
    out, mod = run2(tmp_path, Split)
    assert "25" not in scans(mod)


def test_a_pick_missing_from_both_scans_skips_its_steps_and_the_eat_still_runs(tmp_path):
    out, mod = run2(tmp_path, NoWater)
    assert scans(mod) == ["15", "25"] * 5
    for r in out["readings"]["reps"]:
        assert r["notes"] == ["no_stocked_container_in_scan", "no_water_pick"] and r["pick_water"] is None
        sk = [(s["goal"], s["args"], s["detail"]) for s in r["steps"] if s["state"] == "skipped"]
        assert sk == [("goto", "", "no water pick"), ("loot", "water", "no water pick")]
        assert r["completed"] is False and r["server_eat"]["moved"] is True
    g = G.gate_b(out)
    assert g["completed"] == 0 and g["eats_seen_by_server"] == 5 and g["reasons_in_set"] is True


def test_no_container_keeps_pass1s_path(tmp_path):
    out, mod = run2(tmp_path, no_containers=True)
    assert [c["args"] for c in mod.cmds] == ["15", "25"] * 5 and T1.labels(mod.cmds) == ["scan"] * 10
    for r in out["readings"]["reps"]:
        assert r["notes"] == ["no_container_in_scan", "no_container_in_wide_scan"]
        assert r["pick_food"] is None and r["pick_water"] is None and r["completed"] is False
    assert G.gate_b(out)["completed"] == 0


def test_a_failed_wide_scan_keeps_the_near_pick_and_skips_the_missing_one(tmp_path):
    n25 = math.ceil(51 * 51 / T1.FakeMod.PART_SQUARES)
    out, mod = run2(tmp_path, WaterFar, drop_parts={n25})
    for r in out["readings"]["reps"]:
        assert r["notes"] == ["no_stocked_container_in_scan", "wide_scan_failed", "no_water_pick"]
        assert r["steps"][1]["state"] == "timeout" and r["pick_food"]["x"] == 105 and r["pick_water"] is None
