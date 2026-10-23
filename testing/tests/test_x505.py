"""Offline tests of testing/experiments/x505_smoke.py (Plan 19 Task 9b, never booted here): every grade with a failing
case and its unmeasured case; the predictions; the pre-boot checks on the real repository, the real profile, the real
staged copy and the real fixture; the driver's refusal (read statically: the driver is never invoked); and the session's
body run against test_x50_lib's fake world behind its fake bus, extended with vanilla's in-Eat item-stats packet
(#4147: every part-eat writes the remainder's read-time value on the client) and the mod's re-sync after the restore
(21f788a7), once as predicted and once per defect flag that must move a named grade off as_predicted, and once at the
live bus latency against the budget.

The fake answers the harness's real reply shapes (test_x50_lib's World: `players` a list, {} when nobody is online;
lua.read {ok, side, root, n, values, missing}; witness.fields {side, subject, id, resolved, fields, ...}; eat.action
{queued, fraction, spawned "found", ...}; stats.setany and record.set as their @reply lines)."""
import copy
import os
import shutil
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
EXP = os.path.join(os.path.dirname(HERE), "experiments")
sys.path.insert(0, EXP)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))

import x505_smoke as D                # noqa: E402
import x50_lib as L                   # noqa: E402
import x47_lib as L47                 # noqa: E402
import x48_lib as L48                 # noqa: E402
import xlib as X                      # noqa: E402
import test_x50_lib as T50            # noqa: E402

REPO = D.REPO
SRV, CLI = D.SRV, D.CLI
PROFILE_PATH = os.path.join(REPO, "testing", "profiles", D.PROFILE + ".toml")
FIXTURE_SANDBOX = os.path.join(REPO, "testing", "fixtures", "default", "cache", "server", "Server",
                               "pzt_SandboxVars.lua")
GRADES = {"INI", "OPT_SERVER", "OPT_ADMIN", "MOD_READ", "JOIN", "PRE", "CONTROL", "T7_2", "COUNTS", "Z"}
need_staged = pytest.mark.skipif(not os.path.isdir(os.path.join(REPO, D.STAGE_ROOT)),
                                 reason="release/ (gitignored) not staged on this machine")
ran = any(d.startswith(D.KEY + "-") for d in os.listdir(os.path.join(REPO, "testing", "artifacts")))


# ================================================================ the constants and predictions
def test_the_session_names_its_own_file_profile_and_commit():
    with open(D.__file__, encoding="utf-8") as fh:
        src = fh.read()
    assert 'KEY = "x505"' in src and 'PREFIX = "x505"' in src and 'PROFILE = "x505-smoke"' in src
    assert os.path.basename(D.__file__) == D.DRIVER and D.DRIVER.startswith(D.PREFIX + "_")
    assert D.STAGED_FROM != L.STAGED_FROM                       # never the frozen lib's commit
    assert set(D.PRED) == GRADES and all(D.PRED.values())
    assert D.BUDGET_S <= 400.0


def test_the_predictions():
    p = D.PREDICTED
    assert p["control"] == {"server_field": [5.0, 3.75], "server_readtime_after": 13.75, "client_after": 13.75}
    assert p["t72"]["server_field"] == [3.75, 2.5] and p["t72"]["client_after"] == 12.5
    assert p["t72"]["client_lowered_x503"] == 8.833333                    # x503's 8.833333015441895
    assert abs(D.lowered_client(3.75, 13.75, -0.135, -0.09) - 8.833333015441895) < D.TOL_FIELD
    assert p["counts"] == {"allies": 1, "restores": 1, "alliesFailures": 0}


def test_the_values_are_distinct_from_the_defaults_and_every_earlier_pair(monkeypatch):
    assert D.values_distinct()
    for pace, comb in [(3, 1), (2, 2)] + list(D.PRIOR_SETS.values()):
        monkeypatch.setattr(D, "PACE_SET", pace)
        monkeypatch.setattr(D, "COMBINE_SET", comb)
        assert D.values_distinct() is False, (pace, comb)


def test_the_options_are_the_declared_enums_with_their_defaults():
    import glob
    path = glob.glob(os.path.join(REPO, "mod", "NutritionRevamp", "*", "media", "sandbox-options.txt"))[0]
    text = open(path, encoding="utf-8").read()
    for name, default in (("DeathPace", D.PACE_DEFAULT), ("HealthCombine", D.COMBINE_DEFAULT), ("Mode", 1)):
        block = text.split(f"option NR.{name}\n", 1)[1].split("}", 1)[0]
        assert "type = enum, numValues = " in block and f"default = {default}," in block, name


# ================================================================ the pure grades
def test_grade_ini():
    assert D.grade_ini({"DeathPace": "2", "HealthCombine": "1"})[0] == "as_predicted"
    assert D.grade_ini({"DeathPace": "3", "HealthCombine": "1"})[0] == "falsified"
    assert D.grade_ini({"DeathPace": "2"})[0] == "falsified"
    assert D.grade_ini(None)[0] == "unmeasured"


def lr(values, side=SRV, missing=None):
    return {"ok": True, "side": side, "root": "_G", "n": len(values) + len(missing or {}), "values": dict(values),
            "missing": missing or {}}


def good_sets():
    return {"end": {SRV: lr({D.SERVER_PACE_G: 2, D.SERVER_COMBINE_G: 1, D.MOD_PACE_G: 2, D.MOD_COMBINE_G: 1,
                             D.OPT_PACE_G: 2, D.OPT_COMBINE_G: 1, D.OPT_DAYMIN_G: 90, D.VERSION_G: "1.0.0"}),
                    CLI: lr({D.SERVER_PACE_G: 2, D.SERVER_COMBINE_G: 1, D.VERSION_G: "1.0.0"}, side="client")}}


def test_grade_opt_and_mod_read():
    rs = good_sets()
    assert D.grade_opt(rs, SRV)[0] == "as_predicted" and D.grade_opt(rs, CLI)[0] == "as_predicted"
    assert D.grade_mod_read(rs)[0] == "as_predicted"
    off = copy.deepcopy(rs)
    off["end"][CLI]["values"][D.SERVER_PACE_G] = 3
    assert D.grade_opt(off, CLI)[0] == "falsified" and D.grade_opt(off, SRV)[0] == "as_predicted"
    off = copy.deepcopy(rs)
    off["end"][SRV]["values"][D.OPT_COMBINE_G] = 2
    assert D.grade_mod_read(off)[0] == "falsified"
    miss = copy.deepcopy(rs)
    del miss["end"][SRV]["values"][D.MOD_PACE_G]
    miss["end"][SRV]["missing"] = {D.MOD_PACE_G: "nil"}
    assert D.grade_mod_read(miss)[0] == "unmeasured"
    assert D.grade_opt({"end": {SRV: {"error": "TimeoutError"}}}, SRV)[0] == "unmeasured"
    assert D.grade_opt({}, SRV)[0] == "unmeasured"
    start_only = {"start": rs["end"]}                       # the `start` set is a reading, never graded
    assert D.grade_opt(start_only, SRV)[0] == "unmeasured"


def test_grade_join():
    rows = [{"side": "server", "cmd": "lua.global", "args": "NutritionRevamp.version", "ok": True},
            {"side": "client", "cmd": "lua.global", "args": "NutritionRevamp.version", "ok": True}]
    assert D.grade_join(rows, ["admin"])[0] == "as_predicted"
    assert D.grade_join([rows[0], dict(rows[1], ok=False)], ["admin"])[0] == "falsified"
    assert D.grade_join(rows[:1], ["admin"])[0] == "falsified"                  # no client row
    assert D.grade_join(rows, {})[0] == "falsified"                              # nobody online: the bus's {}
    assert D.grade_join(rows, None)[0] == "unmeasured"
    assert D.grade_join(None, ["admin"])[0] == "unmeasured"


def item(field, rt, hung, wall=100.0, resolved=True):
    return {"fields": {"getUnhappyChangeUnmodified": field, "getUnhappyChange": rt, "getHungChange": hung},
            "resolved": resolved, "wall": wall, "wall_after": wall + 0.5}


def eat(arm, hunger, f0, rt0, h0, f1, rt1, h1, c0, c1, allies=1, landed=True, c_resolved=True, sb=None, sb_wall=None):
    e = {"arm": arm, "tag": arm, "landed": landed, "stats0": {"Hunger": hunger},
         "item0": item(f0, rt0, h0), "item1": item(f1, rt1, h1, wall=100.0),
         "citem0": item(c0, c0, h0), "citem1": item(c1, c1, h1, wall=101.5, resolved=c_resolved),
         "sitem1b": item(*(sb or (f1, rt1, h1)), wall=sb_wall if sb_wall is not None else 103.0),
         "rec1": {"lastIntake.allies": allies}}
    if landed:
        e["frac"] = 1 - h1 / h0
    return e


def x503_like(control_c1=13.75, arm_c1=12.5, arm_f1=2.5, arm_rt1=12.5, hunger=0.32, allies=0.6, **kw):
    """x503's two potato eats (I2C 5 -> 3.75, T72 3.75 -> 2.5), the clients as predicted unless overridden."""
    c = eat(D.CONTROL, 0.002, 5.0, 15.0, -0.18, 3.75, 13.75, -0.135, 15.0, control_c1)
    a = eat(D.ARM, hunger, 3.75, 13.75, -0.135, arm_f1, arm_rt1, -0.09, 13.75, arm_c1, allies=allies, **kw)
    return [c, a]


def test_grade_control():
    assert D.grade_control(x503_like())[0] == "as_predicted"
    assert D.grade_control(x503_like(control_c1=15.0))[0] == "falsified"          # vanilla's packet absent
    assert D.grade_control(x503_like(control_c1=3.75))[0] == "falsified"          # the stored value, not read-time
    eats = x503_like()
    eats[0]["citem1"]["resolved"] = False
    v, obs, _ = D.grade_control(eats)
    assert v == "unmeasured" and "client read did not resolve" in obs["why"]
    eats = x503_like()
    eats[0]["stats0"]["Hunger"] = 0.3
    assert D.grade_control(eats)[0] == "unmeasured"                                # not sated
    eats = x503_like()
    eats[0]["sitem1b"]["fields"]["getUnhappyChange"] = 12.0
    assert D.grade_control(eats)[0] == "unmeasured"                                # the bracket moved
    eats = x503_like()
    eats[0]["sitem1b"]["wall"] = eats[0]["sitem1b"]["wall_after"] = 100.0 + D.PAIR_SLACK_S + 1
    assert D.grade_control(eats)[0] == "unmeasured"                                # the bracket too wide
    assert D.grade_control([])[0] == "unmeasured"


def test_grade_t72_as_predicted_and_x503s_case_falsified():
    v, obs, n = D.grade_t72(x503_like())
    assert v == "as_predicted" and n == 1 and obs["keeps_lowered"] is False
    v, obs, n = D.grade_t72(x503_like(arm_c1=8.833333015441895))                   # x503: the lowered field kept
    assert v == "falsified" and obs["keeps_lowered"] is True
    assert D.grade_t72(x503_like(arm_c1=13.75))[0] == "falsified"                  # the client never updated


def test_grade_t72_falsified_when_the_restore_is_missing():
    # the remainder keeps the lowered field (-1.75 x 2/3): its read-time value is then the lowered one, so a client
    # equal to it would pass a client-only check; the restore check catches it
    low = (-1.75) * 2 / 3
    v, obs, _ = D.grade_t72(x503_like(arm_f1=low, arm_rt1=low + 10, arm_c1=low + 10))
    assert v == "falsified" and "restore" in obs["why"]


def test_grade_t72_unmeasured_cases():
    eats = x503_like()
    eats[0]["citem1"]["resolved"] = False
    v, obs, _ = D.grade_t72(eats)
    assert v == "unmeasured" and "control" in obs["why"]                          # the amendments' unmeasured case
    v, obs, _ = D.grade_t72(x503_like(control_c1=15.0))
    assert v == "unmeasured" and "falsified" in obs["why"]                        # vanilla's packet off: no reference
    assert D.grade_t72(x503_like(hunger=0.2))[0] == "unmeasured"                 # the seed did not hold
    assert D.grade_t72(x503_like(allies=1))[0] == "unmeasured"                    # nothing was lowered
    assert D.grade_t72(x503_like(landed=False))[0] == "unmeasured"
    assert D.grade_t72(x503_like(c_resolved=False))[0] == "unmeasured"
    assert D.grade_t72(x503_like(sb=(2.5, 12.0, -0.09)))[0] == "unmeasured"      # the bracket moved
    assert D.grade_t72(x503_like(sb_wall=100.0 + D.PAIR_SLACK_S + 1))[0] == "unmeasured"
    # a fresh potato (no stale term) where the lowered and read-time values coincide cannot tell the sync apart
    eats = [eat(D.CONTROL, 0.002, 5.0, 5.0, -0.18, 3.75, 3.75, -0.135, 5.0, 3.75),
            eat(D.ARM, 0.32, 3.75, 3.75, -0.135, 2.5, 2.5, -0.09, 3.75, 2.5, allies=1.0)]
    assert D.grade_t72(eats)[0] == "unmeasured"


def test_lowered_client_is_distinct_from_the_read_time_value_at_x503s_numbers():
    low = D.lowered_client(3.75, 13.75, -0.135, -0.09)
    assert abs(low - 12.5) > 1.0


# ================================================================ the pre-boot checks
def _profile():
    import tomllib
    with open(PROFILE_PATH, encoding="utf-8") as fh:
        text = fh.read()
    return tomllib.loads(text), text


def test_the_profile_passes_its_checks_and_each_mutation_fails():
    doc, text = _profile()
    assert all(D.profile_doc_checks(doc, text).values()), D.profile_doc_checks(doc, text)
    muts = [("fixture", lambda d: d.__setitem__("fixture", "two")),
            ("clients", lambda d: d.__setitem__("clients", ["admin", "bob"])),
            ("sleep_off", lambda d: d["server"].__setitem__("SleepAllowed", True)),
            ("mods_staged", lambda d: d["mods"][1].__setitem__("path", "mod/NutritionRevamp")),
            ("nutrition_false", lambda d: d["sandbox"].__setitem__("Nutrition", True)),
            ("day_length", lambda d: d["sandbox"].__setitem__("DayLength", 1)),
            ("nr_block", lambda d: d["sandbox"]["NR"].__setitem__("DeathPace", 3)),
            ("nr_block", lambda d: d["sandbox"]["NR"].__setitem__("Mode", 2)),
            ("nr_block", lambda d: d["sandbox"]["NR"].__setitem__("Severity", 1.0)),
            ("no_override", lambda d: d.__setitem__("client_overrides", {})),
            ("server_timeout", lambda d: d["server"].__setitem__("timeout", 420)),
            ("verify_version", lambda d: d.__setitem__("verify", d["verify"][:1])),
            ("verify_version", lambda d: d["verify"][0].__setitem__("expect", '"value": "0.9.0"'))]
    for key, mut in muts:
        d2 = copy.deepcopy(doc)
        mut(d2)
        assert D.profile_doc_checks(d2, text)[key] is False, key
    assert D.profile_doc_checks(doc, "# testing/profiles/x50-hedonics.toml")["header_names_file"] is False


def test_preboot_on_the_repository():
    pre, ok = D.preboot(D.DRIVER)
    if not os.path.isfile(os.path.join(REPO, L48.FIXTURE_PLAYERS_DB)):
        pytest.skip("the default fixture cache is not provisioned on this machine")
    if not pre["no_prior_artifact"]:
        pytest.skip("x505's artifact is committed: preboot refuses it by design")
    if not pre["staged_from_is_mod_head"]:
        pytest.skip("mod/ moved past STAGED_FROM after the run")
    assert ok, {k: v for k, v in pre.items() if v is not True}


def test_preboot_refuses_a_wrong_file_and_a_prior_artifact(tmp_path):
    pre, ok = D.preboot("x503_allies.py")
    assert ok is False and pre["driver_file"] is False and pre["driver_prefix"] is False
    fake = tmp_path / "repo"
    (fake / "testing" / "artifacts" / "x505-20261023-000000").mkdir(parents=True)
    pre, ok = D.preboot(D.DRIVER, repo=str(fake))
    assert ok is False and pre["no_prior_artifact"] is False


def test_preboot_refuses_a_staged_from_off_mod_head(monkeypatch):
    monkeypatch.setattr(D.L, "mod_head", lambda repo=None: "0123abcd")
    pre, ok = D.preboot(D.DRIVER)
    assert ok is False and pre["staged_from_is_mod_head"] is False


def test_preboot_refuses_a_missing_harness_marker(monkeypatch):
    m = dict(D.HARNESS_MARKERS)
    m["PZTestKit_Client.lua"] = m["PZTestKit_Client.lua"] + ('TK.register("no.such.command", function(',)
    monkeypatch.setattr(D, "HARNESS_MARKERS", m)
    pre, ok = D.preboot(D.DRIVER)
    assert ok is False and pre["harness_markers"] is False


@need_staged
def test_the_staged_upload_copy_is_staged_from_at_1_0_0():
    # a pre-run guard on the live release/ copy while x505 is unrun; after the run the gate is proved on a fresh stage
    # of the pinned commit instead (test_x485's precedent)
    if not ran:
        mg = D.staged_gate()
        assert mg["ok"], mg
        assert mg["staged_version"] == D.STAGED_VERSION and mg["commit"] == D.STAGED_FROM
        head = D.L.mod_head()
        assert D.STAGED_FROM.startswith(head) or head.startswith(D.STAGED_FROM)
        return
    import io
    import subprocess
    import tarfile
    import tempfile
    import release_pack as RP
    with tempfile.TemporaryDirectory() as d:
        arch = subprocess.run(["git", "archive", "--format=tar", D.STAGED_FROM, D.MOD_DIR], cwd=REPO,
                              capture_output=True, check=True)
        with tarfile.open(fileobj=io.BytesIO(arch.stdout)) as tf:
            tf.extractall(os.path.join(d, "src"), filter="data")
        RP.stage(os.path.join(d, "src", *D.MOD_DIR.split("/")), os.path.join(d, "out"))
        root = os.path.join(d, "out", "NutritionRevamp")
        mod = os.path.join(root, "Contents", "mods", "NutritionRevamp")
        mg = D.G.staged_gate(repo=REPO, commit=D.STAGED_FROM, stage_root=root, stage_mod=mod)
        assert mg["ok"], mg
        assert mg["staged_version"] == D.STAGED_VERSION


@pytest.mark.skipif(not os.path.isfile(FIXTURE_SANDBOX), reason="the default fixture's cache (gitignored) absent")
def test_the_seed_merge_of_the_real_fixture_file_holds_the_nr_block(tmp_path):
    from pzt.server import merge_sandbox_vars
    doc, _ = _profile()
    p = tmp_path / "pzt_SandboxVars.lua"
    shutil.copyfile(FIXTURE_SANDBOX, p)
    assert D.grade_ini(L47.sandbox_nr_block(p.read_text(encoding="utf-8")))[0] == "unmeasured"
    merge_sandbox_vars(str(p), doc["sandbox"])
    block = L47.sandbox_nr_block(p.read_text(encoding="utf-8"))
    assert block == {"Mode": "1", "DeathPace": "2", "HealthCombine": "1"}
    assert D.grade_ini(block)[0] == "as_predicted"


def test_the_driver_refuses_arguments_before_main():
    with open(D.__file__, encoding="utf-8") as fh:
        src = fh.read()
    i_ref, i_main = src.index("refusal = parse_argv(sys.argv[1:], __file__)"), src.rindex("    main()")
    assert i_ref < i_main and "sys.exit(refusal)" in src[i_ref:i_main]
    assert src.index('if __name__ == "__main__":') < i_ref
    assert D.parse_argv(["--help"], D.DRIVER) and D.parse_argv(["x"], D.DRIVER)
    assert D.parse_argv([], D.DRIVER) is None


# ================================================================ the body run on the fake world
class World(T50.World):
    """test_x50_lib's world with vanilla's in-Eat item-stats packet (#4147) and the mod's re-sync after its restore
    (21f788a7), the harness's item.set sync, and the session's options. Flags: no_restore_sync (x503's build),
    no_vanilla_packet, seed_fails, pace_off (the server's options poll and K.drain.OPT at the default), admin_default
    (admin's SandboxVars copy at the default); test_x50_lib's no_allies and no_restore."""

    def complete_eat(self, item_id, asked, progress=1.0):
        it = self.items.get(item_id)
        if it is None:
            return super().complete_eat(item_id, asked, progress)
        u0, st, h0 = it["u"], it["state"], it["hung"]
        a0 = self.h["allies"]
        super().complete_eat(item_id, asked, progress)
        it = self.items.get(item_id)
        if it is None:
            return
        f = 1 - it["hung"] / h0
        rt = u0 + st
        allied = self.h["allies"] > a0
        scaled = rt * L.ALLIES_F if allied else rt
        if "no_vanilla_packet" not in self.f:
            it["c_u"] = (u0 - (rt - scaled)) * (1 - f) + st          # vanilla's packet: the lowered field's read-time
        if allied and "no_restore" not in self.f and "no_restore_sync" not in self.f:
            it["c_u"] = it["u"] + st                                  # the mod's sendItemStats after the restore

    def gread(self, path):
        pace, comb = (3, 2) if "pace_off" in self.f else (D.PACE_SET, D.COMBINE_SET)
        table = {D.SERVER_PACE_G: D.PACE_SET, D.SERVER_COMBINE_G: D.COMBINE_SET, D.MOD_PACE_G: pace,
                 D.MOD_COMBINE_G: comb, D.OPT_PACE_G: pace, D.OPT_COMBINE_G: comb, D.OPT_DAYMIN_G: 90}
        return table[path] if path in table else super().gread(path)

    def answer(self, node, cmd, args=""):
        a = args.split() if isinstance(args, str) else []
        if cmd == "stats.setany" and a[1] == "HUNGER" and "seed_fails" in self.f:
            return {"ok": True, "stat": "HUNGER", "side": "server", "requested": float(a[2]),
                    "before": self.stats["Hunger"], "after": self.stats["Hunger"]}
        r = super().answer(node, cmd, args)
        if cmd == "item.set":                                        # the harness syncs with sendItemStats
            it = self.first(a[1])
            it["c_u"] = it["u"] + it["state"]
        if cmd == "lua.read" and node != "server" and "admin_default" in self.f and isinstance(r, dict):
            v = r["values"]
            if D.SERVER_PACE_G in v:
                v[D.SERVER_PACE_G] = D.PACE_DEFAULT
        return r


def body_run(tmp_path, flags=(), wall=None, verify_ok=True):
    w = World(str(tmp_path), flags)
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
           "world_changes": {"left_in_place": []}}
    clients = {"admin": T50.FakeClient(w)}
    xs = X.Xs(out, node=lambda s: s, clients=clients, ask=w.ask, budget_s=D.BUDGET_S, clock=w.clock, sleep=w.sleep,
              spawn_wait_s=0.5, predictions=D.PRED)
    xs.server = T50.FakeServer(w, str(tmp_path))
    xs.path = os.path.join(str(tmp_path), "out.json")
    out["sandbox_seeded"] = {"Mode": "1", "DeathPace": str(D.PACE_SET), "HealthCombine": str(D.COMBINE_SET)}
    out["verify"] = [{"side": "server", "cmd": "lua.global", "args": "NutritionRevamp.version", "ok": True},
                     {"side": "client", "cmd": "lua.global", "args": "NutritionRevamp.version", "ok": verify_ok}]
    S = D.Smoke(xs, run_dir=str(tmp_path))
    S.body_run(S.phases())
    out["logs"] = {"mod_error": []}
    out["admin_lua_error"] = False
    if wall is not None:
        wall["end"] = max(pw.get("end", 0.0) for pw in out["phase_walls"].values())
    S.grade_all()
    assert not out["phase_errors"], out["phase_errors"]
    return {k: v["verdict"] for k, v in out["verdicts"].items()}, out


def test_the_body_run_reads_as_predicted_on_a_correct_world(tmp_path):
    v, out = body_run(tmp_path)
    assert set(v) == GRADES
    off = {k: x for k, x in v.items() if x != "as_predicted"}
    assert not off, (off, {k: out["verdicts"][k]["observed"] for k in off})
    t = out["verdicts"]["T7_2"]["observed"]
    assert abs(t["client_field"][1] - 12.5) < 1e-9 and abs(t["server_field"][1] - 2.5) < 1e-9
    assert out["verdicts"]["T7_2"]["predicted"] == D.PRED["T7_2"]
    assert set(out["read_sets"]) == {"start", "end"}


# each defect with every grade it moves off as_predicted (the first named is the defect's own)
DEFECTS = [
    ("no_restore_sync", {"T7_2"}),
    ("no_restore", {"T7_2", "COUNTS"}),
    ("no_vanilla_packet", {"CONTROL", "T7_2"}),
    ("no_allies", {"T7_2", "COUNTS"}),
    ("seed_fails", {"PRE", "T7_2", "COUNTS"}),
    ("pace_off", {"MOD_READ"}),
    ("admin_default", {"OPT_ADMIN"}),
]


@pytest.mark.parametrize("flag,moved", DEFECTS)
def test_each_defect_moves_its_grades(tmp_path, flag, moved):
    v, out = body_run(tmp_path, (flag,))
    off = {k for k, x in v.items() if x != "as_predicted"}
    assert off == moved, (flag, {k: (v[k], out["verdicts"][k]["observed"]) for k in off | moved})


def test_x503s_build_reads_t7_2_falsified_with_the_lowered_field(tmp_path):
    v, out = body_run(tmp_path, ("no_restore_sync",))
    t = out["verdicts"]["T7_2"]["observed"]
    assert v["T7_2"] == "falsified" and t["keeps_lowered"] is True
    assert abs(t["client_field"][1] - D.PREDICTED["t72"]["client_lowered_x503"]) < 1e-5


def test_the_unmeasured_defects_read_unmeasured_never_falsified(tmp_path):
    for flag in ("no_vanilla_packet", "no_allies", "seed_fails"):
        (tmp_path / flag).mkdir()
        v, _ = body_run(tmp_path / flag, (flag,))
        assert v["T7_2"] == "unmeasured", flag
    (tmp_path / "x").mkdir()
    v, _ = body_run(tmp_path / "x", ("no_vanilla_packet",))
    assert v["CONTROL"] == "falsified"


def test_a_remainder_that_keeps_the_lowered_field_reads_falsified_not_unmeasured(tmp_path):
    v, out = body_run(tmp_path, ("no_restore",))
    assert v["T7_2"] == "falsified" and "restore" in out["verdicts"]["T7_2"]["observed"]["why"]
    assert v["COUNTS"] == "falsified"


def test_z_reads_a_mod_error_line_and_a_failure_counter():
    D0 = {"S": {"hstats": {"NutritionRevamp.server.hedonics.stats.alliesFailures": 0}},
          "C": {"hstats": {"NutritionRevamp.server.hedonics.stats.alliesFailures": 1}}}
    assert L.grade_z({"logs": {"mod_error": []}, "admin_lua_error": False}, {})[0] == "as_predicted"
    assert L.grade_z({"logs": {"mod_error": ["NR_Server_Hedonics.lua failed:"]}, "admin_lua_error": False},
                     {})[0] == "falsified"
    assert L.grade_z({"logs": {"mod_error": []}, "admin_lua_error": False}, D0)[0] == "falsified"


def test_a_failed_verify_row_falsifies_join(tmp_path):
    v, _ = body_run(tmp_path, verify_ok=False)
    assert v["JOIN"] == "falsified"


BOOT_S = 85.0                                 # the session ready 52-85 s after the launch in x491-x495
TEARDOWN_S = 60.0                             # bounded teardown, the log reads and the copy
WALL_MARGIN_S = 60.0


def test_the_body_fits_its_budget_at_live_bus_latency(tmp_path):
    """x50's F2: on the latency-charged fake (1.25 s a server step, 0.35 s a client step), the last phase's end plus the
    boot leaves WALL_MARGIN_S of the budget, and the budget plus the boot and the teardown stays under the Bash call's
    600 s."""
    wall = {}
    v, out = body_run(tmp_path, wall=wall)
    margin = D.BUDGET_S - (wall["end"] + BOOT_S)
    print(f"x505: body {wall['end']:.1f} s, boot {BOOT_S} s, budget {D.BUDGET_S} s, margin {margin:.1f} s")
    assert margin >= WALL_MARGIN_S, (wall["end"], margin)
    assert D.BUDGET_S + BOOT_S + TEARDOWN_S < 600.0
    assert not out.get("budget_stop") and not out.get("skipped_phases")
