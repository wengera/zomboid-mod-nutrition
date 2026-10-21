"""Offline tests of testing/experiments/x485_smoke.py (Plan 17 Task 7b, run x485, the final upload copy's smoke boot):
every grade with an as-predicted case, a failing case and its unmeasured case over a fake bus that answers lua.global in
the harness's shape {side, name, resolved, type, value} (or {side, name, resolved false, failedAt}) and lua.call in
{ok, side, path, nargs, r1} (or {ok false, side, path, failedAt}), with x47_lib's log-reader shapes; the pre-boot checks
on the real repository, the real profile, the real re-staged copy and fixture two's real options file merged as the seed
merges it. The staged-copy and fixture tests skip where release/ or a fixture cache (both gitignored) are absent.
"""
import copy
import os
import shutil
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x485_smoke as D                # noqa: E402
import x47_lib as L47                 # noqa: E402
import xlib as X                      # noqa: E402

REPO = D.REPO
SRV, ADMIN, BOB = D.SRV, D.ADMIN, D.BOB
PROFILE_PATH = os.path.join(REPO, "testing", "profiles", D.PROFILE + ".toml")
FIXTURE_TWO_SANDBOX = os.path.join(REPO, "testing", "fixtures", "two", "cache", "server", "Server",
                                   "pzt_SandboxVars.lua")
need_staged = pytest.mark.skipif(not os.path.isdir(os.path.join(REPO, D.STAGE_ROOT)),
                                 reason="release/ (gitignored) not staged on this machine")
GRADES = {"INI", "OPT_SERVER", "OPT_ADMIN", "OPT_BOB", "MOD_READ", "JOIN", "Z", "NEWKEYS"}
STARVE, IRON = "UI_NR_DrainRec_starvation", "UI_NR_DrainRec_iron"


# ---------------------------------------------------------------- the fake bus
def lg(value, resolved=True, side="server", name="x"):
    if not resolved:
        return {"side": side, "name": name, "resolved": False, "failedAt": "NR"}
    return {"side": side, "name": name, "resolved": True, "type": type(value).__name__, "value": value}


def lc(r1, side="admin", path="getText"):
    if r1 is None:
        return {"ok": False, "side": side, "path": path, "failedAt": path}
    return {"ok": True, "side": side, "path": path, "nargs": 1, "r1": r1}


def values(pace=1, combine=1, mod_pace=1, mod_combine=1, opt_pace=1, opt_combine=1, version="1.0.0"):
    v = {}
    for side in (SRV, ADMIN, BOB):
        v[(side, D.SERVER_PACE_G)] = pace
        v[(side, D.SERVER_COMBINE_G)] = combine
        v[(side, D.VERSION_G)] = version
    v.update({(SRV, D.MOD_PACE_G): mod_pace, (SRV, D.MOD_COMBINE_G): mod_combine, (SRV, D.OPT_PACE_G): opt_pace,
              (SRV, D.OPT_COMBINE_G): opt_combine, (SRV, D.OPT_DAYMIN_G): 15, (SRV, D.READAT_G): "poll"})
    for side in (ADMIN, BOB):
        v[(side, D.MOD_PACE_G)] = 3
        v[(side, D.MOD_COMBINE_G)] = 2
    return v


def texts(**over):
    t = {(s, k): want for s in D.TEXT_SIDES for k, want in D.KEYS.items()}
    t.update(over)
    return t


def fake_ask(vals, txts, calls=None):
    def ask(node, cmd, args, timeout=20):
        if calls is not None:
            calls.append((node, cmd, args))
        if cmd == "lua.global":
            v = vals.get((node, args), "absent")
            return lg(None, resolved=False, side=node, name=args) if v == "absent" else lg(v, side=node, name=args)
        assert cmd == "lua.call" and args.startswith("getText ") and timeout == D.CALL_TIMEOUT_S
        key = args.split(" ", 1)[1]
        r1 = txts.get((node, key), "absent")
        return lc(None if r1 == "absent" else r1, side=node)
    return ask


def take(vals=None, txts=None, nodes=None):
    rs, ts = {}, {}
    nodes = nodes or {SRV: SRV, ADMIN: ADMIN, BOB: BOB}
    ask = fake_ask(vals or values(), txts if txts is not None else texts())
    for tag in ("after_ready", "end"):
        D.L.take_reads(ask, nodes, tag, rs, plan=D.READ_PLAN)
        D.take_texts(ask, nodes, tag, ts)
    return rs, ts


def x485_out(**kw):
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
           "sandbox_seeded": {"DeathPace": "1", "HealthCombine": "1"}, "bob": {"start_wall": 70.0, "ready_wall": 110.0},
           "admin_ready_wall": 60.0, "players_end": ["admin", "bob"], "manifest_gate": {"staged_version": "1.0.0"},
           "logs": {"mod_error": [], "server_mismatch": [],
                    "user": {"fully_connected": ["admin", "bob"], "anticheat_any": [], "read": True}},
           "admin_lua_error": False}
    out.update(kw)
    return out


def grade(vals=None, txts=None, nodes=None, **kw):
    out = x485_out(**kw)
    xs = X.Xs(out, node=lambda s: s)
    rs, ts = take(vals, txts, nodes)
    D.grade_x485(xs, out, rs, ts)
    return {k: x["verdict"] for k, x in out["verdicts"].items()}, out


# ---------------------------------------------------------------- the grades
def test_as_predicted():
    v, out = grade()
    assert set(v) == GRADES and all(x == "as_predicted" for x in v.values()), v
    rd = out["readings"]
    assert rd["client_server_options"][ADMIN] == {D.MOD_PACE_G: 3, D.MOD_COMBINE_G: 2}
    assert rd["server_opt_dayMin"] == 15 and rd["server_readAt"] == "poll"
    assert set(rd["bob_texts"].values()) == {"present"} and len(rd["bob_texts"]) == 4
    nk = out["verdicts"]["NEWKEYS"]["observed"]
    assert nk["n_sets"] == 2 and len(nk["states"]) == 4 and nk["server_version"] == "1.0.0"


@pytest.mark.parametrize("kw,moved", [
    ({"pace": 3}, {"OPT_SERVER", "OPT_ADMIN", "OPT_BOB"}),                   # the declared default
    ({"combine": 2}, {"OPT_SERVER", "OPT_ADMIN", "OPT_BOB"}),
    ({"pace": 2, "combine": 3}, {"OPT_SERVER", "OPT_ADMIN", "OPT_BOB"}),     # x483's file
    ({"mod_pace": 3}, {"MOD_READ"}),
    ({"mod_combine": 3}, {"MOD_READ"}),
    ({"opt_pace": 2}, {"MOD_READ"}),
    ({"opt_combine": 2}, {"MOD_READ"}),
    ({"version": "0.9.0"}, {"JOIN", "NEWKEYS"}),
])
def test_each_wrong_read_moves_its_grade(kw, moved):
    v, _ = grade(values(**kw))
    assert {k for k, x in v.items() if x == "falsified"} == moved, v


def test_one_client_side_off_moves_that_side_only():
    vals = values()
    vals[(BOB, D.SERVER_COMBINE_G)] = 2
    v, _ = grade(vals)
    assert v["OPT_BOB"] == "falsified" and v["OPT_ADMIN"] == "as_predicted" and v["OPT_SERVER"] == "as_predicted"


def test_ini_z_join_and_their_unmeasured_cases():
    assert grade(sandbox_seeded={"DeathPace": "3", "HealthCombine": "2"})[0]["INI"] == "falsified"
    assert grade(sandbox_seeded={"DeathPace": "2", "HealthCombine": "3"})[0]["INI"] == "falsified"
    assert grade(sandbox_seeded={"DeathPace": "1"})[0]["INI"] == "falsified"
    assert grade(sandbox_seeded=None)[0]["INI"] == "unmeasured"
    logs = {"mod_error": ["NR_Kernel_View.lua:311 failed:"], "server_mismatch": [],
            "user": {"fully_connected": ["admin", "bob"], "anticheat_any": [], "read": True}}
    assert grade(logs=logs)[0]["Z"] == "falsified"
    assert grade(admin_lua_error=True)[0]["Z"] == "falsified"
    assert grade(logs={})[0]["Z"] == "unmeasured"
    assert grade(bob={"start_wall": 70.0})[0]["JOIN"] == "falsified"                    # bob never ready
    assert grade(bob={})[0]["JOIN"] == "unmeasured"                                    # bob never started
    anti = copy.deepcopy(x485_out()["logs"])
    anti["user"]["anticheat_any"] = ['Anti-cheat="ChecksumUpdate" is triggered for connection="bob"']
    assert grade(logs=anti)[0]["JOIN"] == "falsified"
    vals = values()
    del vals[(SRV, D.OPT_PACE_G)]
    assert grade(vals)[0]["MOD_READ"] == "unmeasured"
    assert grade(nodes={SRV: SRV, ADMIN: ADMIN, BOB: None})[0]["OPT_BOB"] == "unmeasured"


@pytest.mark.parametrize("over,verdict", [
    ({(ADMIN, STARVE): STARVE}, "falsified"),                                 # a missing key reads as its own name
    ({(ADMIN, IRON): "!" + IRON}, "falsified"),                               # ... after the debug prefix's marker
    ({(ADMIN, IRON): "Iron poisoning"}, "falsified"),                         # another key's text
    ({(ADMIN, STARVE): "*" + D.KEYS[STARVE]}, "as_predicted"),                # a found key under the debug prefix
    ({(ADMIN, STARVE): "absent"}, "unmeasured"),                              # lua.call failedAt: unanswered
    ({(BOB, STARVE): STARVE}, "as_predicted"),                                # bob's texts are a reading
])
def test_newkeys(over, verdict):
    txts = texts(**{})
    for k, val in over.items():
        if val == "absent":
            del txts[k]
        else:
            txts[k] = val
    v, out = grade(txts=txts)
    assert v["NEWKEYS"] == verdict, out["verdicts"]["NEWKEYS"]
    assert {k: x for k, x in v.items() if k != "NEWKEYS"} == {k: "as_predicted" for k in GRADES - {"NEWKEYS"}}
    if (BOB, STARVE) in over:
        assert out["readings"]["bob_texts"]["end:" + STARVE] == "missing"


def test_newkeys_unmeasured_without_admin_or_the_server_version():
    assert grade(nodes={SRV: SRV, ADMIN: None, BOB: BOB})[0]["NEWKEYS"] == "unmeasured"
    vals = values()
    del vals[(SRV, D.VERSION_G)]
    assert grade(vals)[0]["NEWKEYS"] == "unmeasured"
    assert D.grade_newkeys({}, take()[0])[0] == "unmeasured"                  # no text set taken


def test_text_state():
    assert D.text_state(lc("Recovering from starvation"), STARVE, D.KEYS[STARVE]) == \
        ("present", "Recovering from starvation")
    assert D.text_state(lc(STARVE), STARVE, D.KEYS[STARVE])[0] == "missing"
    assert D.text_state(lc("!" + STARVE), STARVE, D.KEYS[STARVE])[0] == "missing"
    assert D.text_state(lc(""), STARVE, D.KEYS[STARVE])[0] == "other"
    assert D.text_state({"ok": True, "r1_type": "userdata"}, STARVE, D.KEYS[STARVE])[0] == "unanswered"
    assert D.text_state({"ok": False, "err": "boom"}, STARVE, D.KEYS[STARVE])[0] == "unanswered"
    assert D.text_state({"error": "TimeoutError: x"}, STARVE, D.KEYS[STARVE])[0] == "unanswered"
    assert D.text_state(None, STARVE, D.KEYS[STARVE])[0] == "unanswered"


def test_take_texts_stops_asking_a_side_after_a_timeout_and_records_a_raise():
    calls = []

    def ask(node, cmd, args, timeout=20):
        calls.append((node, args))
        if node == BOB:
            return {"error": "TimeoutError: no reply in 15 s"}
        if node == ADMIN:
            raise ConnectionError("down")
        return lc("x")
    ts = {}
    for tag in ("after_ready", "end"):
        D.take_texts(ask, {ADMIN: ADMIN, BOB: BOB}, tag, ts)
    assert sum(1 for n, _ in calls if n == BOB) == 2                            # once a set
    row = ts["end"][BOB]
    assert "TimeoutError" in row[STARVE]["error"] and row[IRON]["error"].startswith("skipped: ")
    assert ts["end"][ADMIN][STARVE] == {"error": "ConnectionError: down"}
    assert sum(1 for n, _ in calls if n == ADMIN) == 4                          # a raise is not a timeout
    assert D.take_texts(ask, {}, "x", {})[ADMIN][STARVE] == {"error": "no node"}


# ---------------------------------------------------------------- the pre-boot checks
def test_the_driver_names_its_own_file_profile_and_predictions():
    assert D.KEY == D.PREFIX == "x485" and D.PROFILE == "x48-smoke" and D.ARTIFACT == "smoke.json"
    assert os.path.basename(D.__file__) == "x485_smoke.py"
    assert set(D.PRED) == GRADES
    assert D.BUDGET_S - D.OBS_S - D.CLOSE_RESERVE_S <= 210.0                  # bob started by 210 s (x483's F1)
    assert D.BUDGET_S <= 540.0 and D.SERVER_TIMEOUT_S == 240


def test_the_values_are_off_both_defaults_and_x483s():
    assert D.values_distinct()
    assert (D.PACE_DEFAULT, D.COMBINE_DEFAULT) == (3, 2) and D.X483_SET == (2, 3)
    assert (D.PACE_SET, D.COMBINE_SET) == (1, 1)


def test_the_keys_are_r2s_texts_at_the_staged_commit():
    assert D.keys_at_commit() == D.KEYS
    assert D.keys_at_commit(commit="62de3d5a") == {k: None for k in D.KEYS}  # x483's copy lacked them


def _profile():
    import tomllib
    with open(PROFILE_PATH, encoding="utf-8") as fh:
        text = fh.read()
    return tomllib.loads(text), text


def test_profile_checks_pass_and_fail_each_key():
    doc, text = _profile()
    c = D.profile_doc_checks(doc, text)
    assert all(c.values()), c
    muts = [("fixture", lambda d: d.__setitem__("fixture", "default")),
            ("clients", lambda d: d.__setitem__("clients", ["admin"])),
            ("no_override", lambda d: d.__setitem__("client_overrides", {"bob": {"NutritionRevamp": "x"}})),
            ("sleep_off", lambda d: d["server"].__setitem__("SleepAllowed", True)),
            ("nutrition_false", lambda d: d["sandbox"].__setitem__("Nutrition", True)),
            ("day_length", lambda d: d["sandbox"].__setitem__("DayLength", 4)),
            ("nr_block", lambda d: d["sandbox"]["NR"].__setitem__("DeathPace", 2)),
            ("nr_block", lambda d: d["sandbox"]["NR"].__setitem__("HealthCombine", 3)),
            ("nr_block", lambda d: d["sandbox"]["NR"].__setitem__("VisibilityMode", 3)),
            ("mods_staged", lambda d: d["mods"][1].__setitem__("path", "mod/NutritionRevamp")),
            ("server_timeout", lambda d: d["server"].__setitem__("timeout", 420)),
            ("verify_version", lambda d: d.__setitem__("verify", d["verify"][:2])),
            ("verify_version", lambda d: d["verify"][0].__setitem__("expect", '"value": "0.9.0"'))]
    for key, mut in muts:
        d2 = copy.deepcopy(doc)
        mut(d2)
        assert D.profile_doc_checks(d2, text)[key] is False, key
    assert D.profile_doc_checks(doc, "# testing/profiles/x48-options.toml")["header_names_file"] is False


def test_preboot_on_the_repository():
    pre, ok = D.preboot("x485_smoke.py")
    if not pre["no_prior_artifact"]:
        pytest.skip("x485's artifact is committed: preboot refuses it by design")
    if not pre["staged_from_is_mod_head"]:
        pytest.skip("mod/ moved past STAGED_FROM after the run")
    assert ok, {k: v for k, v in pre.items() if v is not True}


def test_preboot_refuses_a_wrong_file_and_a_prior_artifact(tmp_path):
    pre, ok = D.preboot("x483_options.py")
    assert ok is False and pre["driver_file"] is False and pre["driver_prefix"] is False
    fake = tmp_path / "repo"
    (fake / "testing" / "artifacts" / "x485-20261020-000000").mkdir(parents=True)
    pre, ok = D.preboot("x485_smoke.py", repo=str(fake))
    assert ok is False and pre["no_prior_artifact"] is False


@need_staged
def test_the_staged_upload_copy_is_staged_from_at_1_0_0():
    # a pre-run guard on the live release/ copy while x485 is unrun; once it has run and mod/ moves on, the gate is
    # proved on a fresh stage of the pinned commit instead (test_x48b_lib's precedent)
    arts = os.listdir(os.path.join(REPO, "testing", "artifacts"))
    if not any(d.startswith(D.KEY + "-") for d in arts):
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


@pytest.mark.skipif(not os.path.isfile(FIXTURE_TWO_SANDBOX), reason="fixture two's cache (gitignored) absent")
def test_the_seed_merge_of_the_real_fixture_file_holds_both_options(tmp_path):
    from pzt.server import merge_sandbox_vars
    doc, _ = _profile()
    p = tmp_path / "pzt_SandboxVars.lua"
    shutil.copyfile(FIXTURE_TWO_SANDBOX, p)
    assert D.grade_ini(L47.sandbox_nr_block(p.read_text(encoding="utf-8")))[0] == "unmeasured"
    merge_sandbox_vars(str(p), doc["sandbox"])
    block = L47.sandbox_nr_block(p.read_text(encoding="utf-8"))
    assert block == {"DeathPace": "1", "HealthCombine": "1"}
    assert D.grade_ini(block)[0] == "as_predicted"


def test_gates_refuse_a_staged_copy_off_the_commit(tmp_path):
    class Prof:
        verify = [{"args": "NutritionRevamp.version", "expect": '"value": "1.0.0"'}]
    out = {"doctor_clean": True, "harness_lua_dirty": False, "meta": {}}
    xs = X.Xs(out, node=lambda s: s)
    with pytest.raises(SystemExit):
        D._gates(xs, out, Prof(), str(tmp_path), lambda p: [], [],
                 gate=lambda: {"ok": False, "staged_version": "1.0.0"})
    assert "does not match" in out["error"]
    out2 = {"doctor_clean": False, "harness_lua_dirty": False, "meta": {}}
    with pytest.raises(SystemExit):
        D._gates(X.Xs(out2, node=lambda s: s), out2, Prof(), str(tmp_path), lambda p: [], [])
    assert "doctor" in out2["error"]
