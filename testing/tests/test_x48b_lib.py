"""Offline tests of testing/experiments/x48b_lib.py and x48b_prerun.py (Plan 17 Task 7, runs x483 and x484): every grade
with a failing case and its unmeasured case; the pre-boot checks on the real repository, the real re-staged upload copy,
the real fixtures and the real options file merged as the seed merges it; the prerun current at HEAD with the mod's own
creation body; x484's body run against a fake world behind a fake bus, once as predicted and once per defect flag that
must move a named grade off as_predicted; and x483's grades over a fake bus and a fake artifact.

x484's fake world is test_x48_lib's World (the mod itself on the replay host, stepped a game minute at a time as the
fake clock passes, the ring row read before each drain, the harness's real reply shapes), built here from the first
sight with no typed weight (the creation body) at x484's options; a defect flag patches that world's kernel or its
writes. The grading replays the real HEAD replay against the fake ring, so the as-predicted run also checks the write
placement and the replay inputs end to end.

x483's fake bus answers lua.global in the harness's shape {side, name, resolved, type, value} (or {side, name, resolved
false, failedAt}); its log facts are x47_lib's readers' shapes. The staged-copy and fixture tests skip where release/ or
a fixture cache (both gitignored) are absent.
"""
import copy
import json
import os
import re
import shutil
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x48b_lib as L                  # noqa: E402
import x48b_prerun as PR              # noqa: E402
import x48_lib as L48                 # noqa: E402
import xlib as X                      # noqa: E402
import replay_live as RL              # noqa: E402
import test_x48_lib as T48            # noqa: E402

REPO = L.REPO
KERNEL = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Kernel_Drain.lua")
FIXTURE_TWO_SANDBOX = os.path.join(REPO, "testing", "fixtures", "two", "cache", "server", "Server",
                                   "pzt_SandboxVars.lua")
X481_START = os.path.join(REPO, "testing", "artifacts", "x481-20261020-070821", "start.json")
need_staged = pytest.mark.skipif(not os.path.isdir(os.path.join(REPO, L.STAGE_ROOT)),
                                 reason="release/ (gitignored) not staged on this machine")


# ---------------------------------------------------------------- x484's fake world
PATCH = {
    "no_floor": "NutritionRevamp.kernel.drain.rVanilla = function(code, dayMin) return nil end",
    "steep_line": "NutritionRevamp.kernel.drain.STARVE_DBMI = NutritionRevamp.kernel.drain.STARVE_DBMI * 1.05",
    "worst": "NutritionRevamp.kernel.drain.fold = function(acc, f, c) return math.min(acc, f) end",
    "add": "NutritionRevamp.kernel.drain.fold = function(acc, f, c) return acc - (1 - f) end",
    "half_take": ("local D0 = NutritionRevamp.kernel.drain; local t0 = D0.take; "
                  "D0.take = function(D, h) return 0.5 * t0(D, h) end"),
}


class World(T48.World):
    """test_x48_lib's World at x484's options, from the first sight with no typed weight (the creation body)."""

    def __init__(self, results_dir, key="x484", flags=()):
        self.dir = results_dir
        self.f = set(flags)
        prof = L.PROFILES[L.SESSIONS[key]["profile"]]
        pace = 2 if "opt_wrong" in self.f else prof["pace"]
        self.be = RL.ServerReplay(hour_offset=L48.HOUR_OFFSET, rng="half", sleep_allowed=False,
                                  stats=dict(L48.FIRST_SIGHT["stats"]), player=dict(PR.FIRST_SIGHT_PLAYER),
                                  death_pace=pace, health_combine=prof["combine"], day_minutes=L.DAY_MIN,
                                  game_heal=True)
        T48.lua51 = self.be.lua51
        for k, src in PATCH.items():
            if k in self.f:
                self.be.rt.execute(src)
        self.t, self.speed = 0.0, 1.0
        self.age = L48.FIRST_SIGHT["age"] - 1.0 / 60.0
        self.k = 0
        self.ring, self.ring_on, self.paths, self.s = [], False, [], 0
        self.delayed = []
        self.dead = False
        self.saves = 0
        self.step_minute()                                     # the first sight


def run_session(tmp_path, flags=(), budget=1e9):
    d = str(tmp_path)
    os.makedirs(d, exist_ok=True)
    w = World(d, "x484", flags)
    T48.fake_lread_saves(w)
    out = T48.fresh_out()
    xs = X.Xs(out, node=lambda side: side, clients={"admin": T48.FakeClient("admin")}, ask=w.ask, budget_s=budget,
              clock=w.clock, sleep=w.sleep, spawn_wait_s=0.5)
    xs.server = T48.FakeServer(w, d)
    S = L.Sess(xs, "x484", run_dir=d)
    for _ in range(int(0.25 * 60)):                            # S/H take game time before the seed, as live
        w.sleep(w.GH_S / 60.0)
    S.body_run(S.phases())
    out["logs"] = {"mod_error": []}
    out["admin_lua_error"] = False
    S.grade_all()
    v = {k: x["verdict"] for k, x in out["verdicts"].items()}
    return v, out, w, S


def bad(v, out):
    return {k: (x, out["verdicts"][k]["observed"]) for k, x in v.items() if x != "as_predicted"}


NAMES = {
    "x483": {"INI", "OPT_SERVER", "OPT_ADMIN", "OPT_BOB", "MOD_READ", "JOIN", "Z"},
    "x484": {"OPT", "ONSET", "LINE", "RATE", "TRACK", "BERI_ON", "COMBINE", "REPLAY_health", "REPLAY_drain.target", "H1",
             "RING", "Z"},
}


@pytest.fixture(scope="module")
def as_predicted(tmp_path_factory):
    return run_session(tmp_path_factory.mktemp("x484"))


def test_x484_as_predicted(as_predicted):
    v, out, w, S = as_predicted
    assert set(v) == NAMES["x484"]
    assert not bad(v, out), bad(v, out)
    assert not out["phase_errors"] and not out.get("skipped_phases")
    assert out["replay"]["fields"]["health"]["n"] > 150 and out["replay"]["fields"]["drain.target"]["n"] > 150
    assert list(out["phase_walls"]) == ["S", "H", "W", "A", "O", "B", "P", "C", "R"]


def test_x484_reads_as_its_prerun(as_predicted):
    v, out, w, S = as_predicted
    p = L.load_prerun()["x484"]
    ln = out["verdicts"]["LINE"]["observed"]
    assert ln["bmi0"] == pytest.approx(p["line"]["bmi0"], abs=1e-3)       # the onset's age moves the smoothed estimate
    assert ln["slope_h"] == pytest.approx(p["line"]["slope_h"], rel=1e-4) and ln["n"] >= 110
    rt = out["verdicts"]["RATE"]["observed"]
    assert rt["n_starve"] > 100 and rt["n_starve_beri"] > 50 and rt["floor_day"] == pytest.approx(85.536)
    cb = out["verdicts"]["COMBINE"]["observed"]
    assert cb["sep_add_max"] > 1e-4 and cb["sep_worst_max"] > 0.1
    assert out["checks"]["B"]["set_p"]["reply"]["ok"] is True
    start = json.load(open(os.path.join(w.dir, "start.json"), encoding="utf-8"))
    body = start["rec"]["body"]
    assert body["lm"] + body["fm"] == pytest.approx(65.025, abs=1e-9)        # the creation body, never a typed weight


FLAGS = [
    ("opt_wrong", {"OPT"}),
    ("no_onset", {"ONSET"}),
    ("no_floor", {"RATE"}),
    ("steep_line", {"LINE", "REPLAY_drain.target"}),
    ("worst", {"COMBINE"}),
    ("add", {"COMBINE"}),
    ("half_take", {"REPLAY_health", "TRACK"}),
    ("no_beri", {"BERI_ON", "COMBINE", "RATE"}),
]


@pytest.mark.parametrize("flag,grades", FLAGS)
def test_each_defect_moves_its_grade(flag, grades, tmp_path):
    v, out, w, S = run_session(tmp_path, flags=(flag,))
    moved = {k for k, x in v.items() if x != "as_predicted"}
    assert grades <= moved, (flag, bad(v, out))


def test_add_and_no_floor_pass_the_replay_tolerance_so_only_their_grades_catch_them(tmp_path):
    # the Add fold parts from the product by about 1.5e-4 and the floor moves no health on a line this slow: both
    # sit inside REPLAY_TOL, so COMBINE's exact tolerance and RATE are what catch them
    for flag, grade in (("add", "COMBINE"), ("no_floor", "RATE")):
        v, out, w, S = run_session(tmp_path / flag, flags=(flag,))
        assert v[grade] == "falsified" and v["REPLAY_drain.target"] == "as_predicted", (flag, bad(v, out))


def test_the_budget_stops_the_scenario_and_keeps_the_closing_phases(tmp_path):
    v, out, w, S = run_session(tmp_path, budget=150.0)
    assert out["budget_stop"]
    assert {"C", "R"} <= set(out["phase_walls"])


# ---------------------------------------------------------------- x484's pure grades
def _rows(n, a0=3.0, **fields):
    return T48._rows(n, a0, **fields)


def _line_rows(n=60, on=3, bmi0=22.487, scale=1.0, mask=1, pS_off=0.0, bRate=None):
    per_h = L.K_STARVE_DBMI / (bmi0 - 12.0) * scale
    rows = _rows(n, **{"drain.active": lambda i: i >= on, "drain.starveAcute": lambda i: i >= on})
    for i, r in enumerate(rows):
        if i < on:
            continue
        p = per_h * (rows[i - 1]["age"] - rows[on - 1]["age"])
        r.update({"drain.mask": mask, "drain.pS": p + pS_off, L.F1: 1.0 - p, "drain.target": 100.0 * (1.0 - p),
                  "drain.bmi0": bmi0, "drain.bRate": L.K_STARVE_DBMI if bRate is None else bRate})
    return rows


def test_grade_line():
    rows = _line_rows()
    v, o = L.grade_line(rows, 3)
    assert v == "as_predicted" and o["rel"] < 1e-9 and o["n"] == 57
    assert L.grade_line(_line_rows(scale=1.05), 3)[0] == "falsified"            # a steeper line
    assert L.grade_line(_line_rows(pS_off=1e-6), 3)[0] == "falsified"           # frac.1 off 1 - pS
    assert L.grade_line(_line_rows(bRate=L.K_STARVE_DBMI * 1.001), 3)[0] == "falsified"
    r2 = _line_rows()
    r2[20]["drain.target"] += 1e-5
    assert L.grade_line(r2, 3)[0] == "falsified"                                # target off 100 x frac.1
    assert L.grade_line(rows, 3, 20)[0] == "unmeasured"                         # under LINE_MIN_ROWS
    assert L.grade_line(_line_rows(mask=5), 3)[0] == "unmeasured"               # no starvation-alone row
    assert L.grade_line(rows, None)[0] == "unmeasured"


def _rate_rows(n1=10, n5=10, r1=85.536, r5=None):
    r5 = 85.536 + 100.0 * 24.0 / 840.0 if r5 is None else r5
    rows = _rows(n1 + n5, **{"drain.active": True, L48.OPT_DAYMIN: 90.0, "drain.bmi0": 22.487,
                             "drain.mask": lambda i: 1 if i < n1 else 5,
                             "drain.rate": lambda i: r1 if i < n1 else r5})
    return rows


def test_grade_rate():
    assert L.grade_rate(_rate_rows())[0] == "as_predicted"
    assert L.grade_rate(_rate_rows(r1=1.04))[0] == "falsified"                  # the line's own rate: no floor
    assert L.grade_rate(_rate_rows(r5=85.536))[0] == "falsified"                # beriberi's rate left out
    assert L.grade_rate(_rate_rows(r1=85.536 * 1.02))[0] == "falsified"         # over the floor
    assert L.grade_rate(_rate_rows(n5=0))[0] == "unmeasured"
    assert L.grade_rate(_rate_rows(n1=0))[0] == "unmeasured"
    assert L.grade_rate([])[0] == "unmeasured"


def _comb_rows(n=30, fold=None, combine=2):
    rows = _rows(n, **{L.F1: lambda i: 0.999 - 1e-5 * i, L.F3: lambda i: 1.0 - 2e-5 * i,
                       L48.OPT_COMBINE: combine, "drain.mask": 5})
    for r in rows:
        f1, f3 = r[L.F1], r[L.F3]
        r["drain.target"] = 100.0 * (fold(f1, f3) if fold else f1 * f3)
    return rows


def test_grade_combine():
    rows = _comb_rows()
    a = rows[0]["age"] - 0.001
    v, o = L.grade_combine(rows, a)
    assert v == "as_predicted" and o["sep_add_max"] > L.COMBINE_SEP * L.COMBINE_TOL
    assert L.grade_combine(_comb_rows(fold=min), a)[0] == "falsified"
    assert L.grade_combine(_comb_rows(fold=lambda x, y: x - (1 - y)), a)[0] == "falsified"   # Add
    assert L.grade_combine(_comb_rows(combine=3), a)[0] == "falsified"
    flat = _rows(30, **{L.F1: 0.9999, L.F3: 1.0, L48.OPT_COMBINE: 2, "drain.target": 99.99, "drain.mask": 5})
    assert L.grade_combine(flat, a)[0] == "unmeasured"                          # Multiply and Add inseparable
    assert L.grade_combine(rows, rows[-5]["age"])[0] == "unmeasured"            # under COMBINE_MIN_ROWS after it
    assert L.grade_combine(rows, None)[0] == "unmeasured"


# ---------------------------------------------------------------- the constants and the prerun
def _kernel_value(name):
    """K.drain.<name> as the mod writes it: its registry row's value since Plan 19 Task 3g moved the drain dials (the
    kernel line names no number), else the kernel line's literal (a vanilla mirror left in place, R_HUNGER)."""
    tools = os.path.join(REPO, "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import dials
    values = dials.values()
    if "drain." + name in values:
        return float(values["drain." + name])
    with open(KERNEL, encoding="utf-8") as fh:
        m = re.search(r"^K\.drain\.%s = ([0-9.eE+-]+)" % name, fh.read(), re.M)
    return float(m.group(1))


def test_the_kernel_constants_are_the_kernels():
    assert _kernel_value("STARVE_DPDT") == L48.K_STARVE_DPDT
    assert _kernel_value("CAL_BMI0") == L48.K_CAL_BMI0
    assert _kernel_value("BMI_DEATH") == L48.K_BMI_DEATH
    assert _kernel_value("BERIBERI_DEATH_H") == L.K_BERIBERI_DEATH_H
    assert _kernel_value("R_HUNGER") == L48.K_R_HUNGER
    be = PR.backend(3, 2)
    assert float(be.rt.eval("NutritionRevamp.kernel.drain.STARVE_DBMI")) == L.K_STARVE_DBMI


def test_the_committed_prerun_is_the_head_replay():
    have = L.load_prerun()
    now = PR.canonical(PR.compute())
    assert have.get("x484") == now["x484"]
    assert "weight" not in have["_provenance"]["first_sight"]["player"]
    assert PR.main(["--check"]) == 0


def test_the_prerun_command_names_staleness(tmp_path, monkeypatch):
    p = tmp_path / "pr.json"
    p.write_text(json.dumps({"x484": {"x": 1}}), encoding="utf-8")
    monkeypatch.setattr(L, "PRERUN_FILE", os.path.relpath(str(p), REPO))
    assert PR.main(["--check"]) == 1


def test_the_prerun_body_is_the_live_creation_body():
    p = L.load_prerun()["x484"]
    with open(X481_START, encoding="utf-8") as fh:
        body = json.load(fh)["rec"]["body"]
    assert p["body"]["lm"] == pytest.approx(body["lm"], abs=1e-6) and p["body"]["fm"] == pytest.approx(body["fm"],
                                                                                                         abs=1e-6)
    assert p["body"]["kg"] == pytest.approx(sum(L.CREATION_BODY), abs=1e-6)


def test_the_prerun_predicts_the_grades_as_predicted():
    p = L.load_prerun()["x484"]
    assert p["line"]["n_off"] == 0 and p["line"]["rel"] < 1e-6 and p["line"]["n"] >= L.LINE_MIN_ROWS
    assert p["rate"]["n_off"] == 0 and p["rate"]["n_under"] == 0 and p["rate"]["n_starve_beri"] > 0
    assert p["beri"]["lag_gm"] <= L48.BERI_GM and p["combine"]["n_off"] == 0
    assert p["combine"]["sep_add_max"] > 10 * L.COMBINE_SEP * L.COMBINE_TOL
    assert p["health_gap_max"] < L48.REPLAY_TOL["health"][1]
    assert p["onset_after_seed_h"] <= L48.SEED_LEAD_H + L48.ONSET_SLACK_H


# ---------------------------------------------------------------- the pre-boot checks
@pytest.mark.parametrize("key", sorted(L.SESSIONS))
def test_preboot_on_the_repository(key):
    pre, ok = L.preboot(key, L.SESSIONS[key]["driver"])
    if not pre["no_prior_artifact"]:
        pytest.skip("the session's artifact is committed: preboot refuses it by design")
    if key == "x484" and not pre["fixture_fresh"] and not os.path.isfile(os.path.join(REPO, L48.FIXTURE_PLAYERS_DB)):
        pytest.skip("the default fixture cache is not provisioned on this machine")
    assert ok, {k: v for k, v in pre.items() if v is not True}


def test_preboot_refuses_a_wrong_file_a_stale_prerun_and_a_prior_artifact(tmp_path):
    assert L.preboot("x483", "x484_line.py")[1] is False
    assert L.preboot("x484", "x483_options.py")[1] is False
    assert L.preboot("x485", "x485_x.py")[1] is False
    stale = L.preboot("x484", "x484_line.py", compute=lambda keys: {"x484": {"x": 1}})
    assert stale[1] is False and stale[0]["prerun_current"] is False
    fake = tmp_path / "repo"
    (fake / "testing" / "artifacts" / "x483-20261020-000000").mkdir(parents=True)
    pre, ok = L.preboot("x483", "x483_options.py", repo=str(fake))
    assert ok is False and pre["no_prior_artifact"] is False


def test_profile_checks_fail_each_key():
    import tomllib
    for name in L.PROFILES:
        path = os.path.join(REPO, "testing", "profiles", name + ".toml")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        doc = tomllib.loads(text)
        c = L.profile_doc_checks(name, doc, text)
        assert all(c.values()), (name, c)
        other = "default" if doc["fixture"] == "two" else "two"
        for key, (k, v) in {"fixture": ("fixture", other), "clients": ("clients", ["bob"]),
                            "no_override": ("client_overrides", {"bob": {"NutritionRevamp": "x"}})}.items():
            d2 = copy.deepcopy(doc)
            d2[k] = v
            assert L.profile_doc_checks(name, d2, text)[key] is False, (name, key)
        for key, sub, k, v in (("sleep_off", "server", "SleepAllowed", True),
                               ("nutrition_false", "sandbox", "Nutrition", True),
                               ("day_length", "sandbox", "DayLength", 2)):
            d2 = copy.deepcopy(doc)
            d2[sub][k] = v
            assert L.profile_doc_checks(name, d2, text)[key] is False, (name, key)
        for leaf in ("DeathPace", "HealthCombine"):
            d2 = copy.deepcopy(doc)
            d2["sandbox"]["NR"][leaf] = 1
            assert L.profile_doc_checks(name, d2, text)["nr_block"] is False
        d2 = copy.deepcopy(doc)
        d2["sandbox"]["NR"]["VisibilityMode"] = 3
        assert L.profile_doc_checks(name, d2, text)["nr_block"] is False
        d2 = copy.deepcopy(doc)
        d2["mods"][1]["path"] = "mod/NutritionRevamp"
        assert L.profile_doc_checks(name, d2, text)["mods_staged"] is False
        d2 = copy.deepcopy(doc)
        d2["server"]["timeout"] = 420
        assert L.profile_doc_checks(name, d2, text)["server_timeout"] is False
        d2 = copy.deepcopy(doc)
        d2["verify"] = d2["verify"][:1]
        assert L.profile_doc_checks(name, d2, text)["verify_version"] is False
        assert L.profile_doc_checks(name, doc, "# other")["header_names_file"] is False
    assert L.profile_doc_checks("x48-curve", {}, "") == {"known_profile": False}


def test_the_drivers_name_their_own_file_profile_and_artifact():
    import importlib
    for key, s in L.SESSIONS.items():
        m = importlib.import_module(s["driver"][:-3])
        assert m.KEY == key and m.PREFIX == key and m.PROFILE == s["profile"] and m.ARTIFACT == s["artifact"]
        assert set(m.PRED) == NAMES[key]
        assert m.BUDGET_S <= 540.0


@need_staged
def test_the_staged_upload_copy_is_mod_head_at_1_0_0():
    # a pre-run guard on the live release/ copy while a session is unrun; once x483 and x484 have run, mod/ and the
    # upload copy move on (the Plan 17 close fix wave re-staged it) and the gate is proved on a fresh stage of the
    # pinned commit instead (x45g's precedent), the committed artifacts being the evidence
    arts = os.listdir(os.path.join(REPO, "testing", "artifacts"))
    if not all(any(d.startswith(k + "-") for d in arts) for k in L.SESSIONS):
        mg = L.staged_gate()
        assert mg["ok"], mg
        assert mg["staged_version"] == L.STAGED_VERSION and mg["commit"] == L.STAGED_FROM
        assert L.STAGED_FROM.startswith(L.mod_head()) or L.mod_head().startswith(L.STAGED_FROM)
        return
    import io
    import tarfile
    import tempfile
    import subprocess
    import release_pack as RP
    with tempfile.TemporaryDirectory() as d:
        arch = subprocess.run(["git", "archive", "--format=tar", L.STAGED_FROM, L.MOD_DIR], cwd=REPO,
                              capture_output=True, check=True)
        with tarfile.open(fileobj=io.BytesIO(arch.stdout)) as tf:
            tf.extractall(os.path.join(d, "src"), filter="data")
        RP.stage(os.path.join(d, "src", *L.MOD_DIR.split("/")), os.path.join(d, "out"))
        root = os.path.join(d, "out", "NutritionRevamp")
        mod = os.path.join(root, "Contents", "mods", "NutritionRevamp")
        mg = L.G.staged_gate(repo=REPO, commit=L.STAGED_FROM, stage_root=root, stage_mod=mod)
        assert mg["ok"], mg
        assert mg["staged_version"] == L.STAGED_VERSION and mg["commit"] == L.STAGED_FROM


def test_the_harness_markers_and_the_fixture_are_x48s():
    found, ok = L48.harness_markers_ok()
    assert ok, found
    fr = L48.fixture_fresh()
    if not os.path.isfile(os.path.join(REPO, L48.FIXTURE_PLAYERS_DB)):
        pytest.skip("the default fixture cache is not provisioned on this machine")
    assert fr["fresh"], fr


# ---------------------------------------------------------------- x483: the options file
@pytest.mark.skipif(not os.path.isfile(FIXTURE_TWO_SANDBOX), reason="fixture two's cache (gitignored) absent")
def test_the_seed_merge_of_the_real_fixture_file_holds_both_options(tmp_path):
    import tomllib
    from pzt.server import merge_sandbox_vars
    with open(os.path.join(REPO, "testing", "profiles", "x48-options.toml"), "rb") as fh:
        sandbox = tomllib.load(fh)["sandbox"]
    p = tmp_path / "pzt_SandboxVars.lua"
    shutil.copyfile(FIXTURE_TWO_SANDBOX, p)
    assert L.grade_ini(L47_block(p))[0] == "unmeasured"                       # the fixture carries no NR block
    merge_sandbox_vars(str(p), sandbox)
    block = L47_block(p)
    assert block == {"DeathPace": "2", "HealthCombine": "3"}
    assert L.grade_ini(block)[0] == "as_predicted"


def L47_block(p):
    import x47_lib
    return x47_lib.sandbox_nr_block(p.read_text(encoding="utf-8"))


def test_grade_ini():
    assert L.grade_ini({"DeathPace": "2", "HealthCombine": "3"})[0] == "as_predicted"
    assert L.grade_ini({"DeathPace": "3", "HealthCombine": "3"})[0] == "falsified"      # the pace's default
    assert L.grade_ini({"DeathPace": "2", "HealthCombine": "2"})[0] == "falsified"      # the combine's default
    assert L.grade_ini({"DeathPace": "2"})[0] == "falsified"
    assert L.grade_ini(None)[0] == "unmeasured"


# ---------------------------------------------------------------- x483: the reads and the grades
def lg(value, resolved=True, side="server", name="x"):
    """A lua.global reply in the harness's shape."""
    if not resolved:
        return {"side": side, "name": name, "resolved": False, "failedAt": "NR"}
    return {"side": side, "name": name, "resolved": True, "type": type(value).__name__, "value": value}


def fake_ask(values):
    def ask(node, cmd, args, timeout=20):
        assert cmd == "lua.global"
        v = values.get((node, args), "absent")
        if v == "absent":
            return lg(None, resolved=False, side=node, name=args)
        return lg(v, side=node, name=args)
    return ask


def all_values(pace=2, combine=3, mod_pace=2, mod_combine=3, opt_pace=2, opt_combine=3, version="1.0.0"):
    v = {}
    for side in (L.SRV, L.ADMIN, L.BOB):
        v[(side, L.SERVER_PACE_G)] = pace
        v[(side, L.SERVER_COMBINE_G)] = combine
        v[(side, L.VERSION_G)] = version
    v.update({(L.SRV, L.MOD_PACE_G): mod_pace, (L.SRV, L.MOD_COMBINE_G): mod_combine,
              (L.SRV, L.OPT_PACE_G): opt_pace, (L.SRV, L.OPT_COMBINE_G): opt_combine, (L.SRV, L.OPT_DAYMIN_G): 15,
              (L.SRV, "NutritionRevamp.server.options.readAt"): "poll"})
    for side in (L.ADMIN, L.BOB):
        v[(side, L.MOD_PACE_G)] = 3
        v[(side, L.MOD_COMBINE_G)] = 2
    return v


def take(values, nodes=None):
    rs = {}
    nodes = nodes or {L.SRV: L.SRV, L.ADMIN: L.ADMIN, L.BOB: L.BOB}
    for tag in ("after_ready", "end"):
        L.take_reads(fake_ask(values), nodes, tag, rs)
    return rs


def x483_out(**kw):
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
           "sandbox_seeded": {"DeathPace": "2", "HealthCombine": "3"}, "bob": {"start_wall": 70.0, "ready_wall": 110.0},
           "admin_ready_wall": 60.0, "players_end": ["admin", "bob"], "manifest_gate": {"staged_version": "1.0.0"},
           "logs": {"mod_error": [], "server_mismatch": [],
                    "user": {"fully_connected": ["admin", "bob"], "anticheat_any": [], "read": True}},
           "admin_lua_error": False}
    out.update(kw)
    return out


def grade(values=None, nodes=None, **kw):
    out = x483_out(**kw)
    xs = X.Xs(out, node=lambda s: s)
    rs = take(values or all_values(), nodes)
    L.grade_x483(xs, out, rs)
    return {k: x["verdict"] for k, x in out["verdicts"].items()}, out


def test_x483_as_predicted():
    v, out = grade()
    assert set(v) == NAMES["x483"] and all(x == "as_predicted" for x in v.values()), v
    rd = out["readings"]["client_server_options"]
    assert rd["admin"] == {L.MOD_PACE_G: 3, L.MOD_COMBINE_G: 2} and rd["predicted"] == rd["bob"]
    assert out["readings"]["server_opt_dayMin"] == 15


@pytest.mark.parametrize("kw,moved", [
    ({"pace": 3}, {"OPT_SERVER", "OPT_ADMIN", "OPT_BOB"}),
    ({"combine": 2}, {"OPT_SERVER", "OPT_ADMIN", "OPT_BOB"}),
    ({"mod_pace": 3}, {"MOD_READ"}),
    ({"opt_combine": 2}, {"MOD_READ"}),
    ({"version": "0.9.0"}, {"JOIN"}),
])
def test_x483_each_wrong_read_moves_its_grade(kw, moved):
    v, out = grade(all_values(**kw))
    assert moved <= {k for k, x in v.items() if x == "falsified"}, v


def test_x483_a_client_option_off_on_one_side_moves_that_side_only():
    vals = all_values()
    vals[(L.BOB, L.SERVER_COMBINE_G)] = 2
    v, out = grade(vals)
    assert v["OPT_BOB"] == "falsified" and v["OPT_ADMIN"] == "as_predicted" and v["OPT_SERVER"] == "as_predicted"


def test_x483_unmeasured_and_the_preconditions():
    vals = all_values()
    del vals[(L.SRV, L.OPT_PACE_G)]
    v, _ = grade(vals)
    assert v["MOD_READ"] == "unmeasured"
    v, _ = grade(nodes={L.SRV: L.SRV, L.ADMIN: L.ADMIN, L.BOB: None})
    assert v["OPT_BOB"] == "unmeasured"
    v, _ = grade(sandbox_seeded={"DeathPace": "3", "HealthCombine": "2"})
    assert v["INI"] == "falsified"
    v, _ = grade(bob={"start_wall": 70.0})
    assert v["JOIN"] == "falsified"
    v, _ = grade(bob={})
    assert v["JOIN"] == "unmeasured"
    v, _ = grade(logs={"mod_error": ["NR_Server_Options.lua:1 failed:"], "server_mismatch": [],
                       "user": {"fully_connected": ["admin", "bob"], "anticheat_any": [], "read": True}})
    assert v["Z"] == "falsified"


def test_take_reads_follows_the_plan_and_records_a_raise():
    def boom(node, cmd, args, timeout=20):
        raise TimeoutError("no reply")
    rs = {}
    L.take_reads(boom, {L.SRV: L.SRV, L.ADMIN: L.ADMIN, L.BOB: L.BOB}, "end", rs)
    assert set(rs["end"][L.SRV]) == set(L.READ_PLAN[L.SRV])
    assert rs["end"][L.BOB][L.SERVER_PACE_G] == {"error": "TimeoutError: no reply"}
    assert L.grade_pair(rs, L.BOB, L.SERVER_PACE_G, L.SERVER_COMBINE_G)[0] == "unmeasured"


def test_take_reads_stops_asking_a_side_after_a_timeout():
    calls = []

    def ask(node, cmd, args, timeout=20):
        calls.append((node, args))
        if node == L.BOB:
            return {"error": "TimeoutError: no reply in 15 s"}
        return lg(2, side=node, name=args)
    rs = {}
    for tag in ("after_ready", "end"):
        L.take_reads(ask, {L.SRV: L.SRV, L.ADMIN: L.ADMIN, L.BOB: L.BOB}, tag, rs)
    assert sum(1 for n, _ in calls if n == L.BOB) == 2                         # once a set
    row = rs["end"][L.BOB]
    first = L.READ_PLAN[L.BOB][0]
    assert "TimeoutError" in row[first]["error"]
    assert all(row[n]["error"].startswith("skipped: ") for n in L.READ_PLAN[L.BOB][1:])
    assert len([n for n, _ in calls if n == L.ADMIN]) == 2 * len(L.READ_PLAN[L.ADMIN])
    assert L.grade_pair(rs, L.BOB, L.SERVER_PACE_G, L.SERVER_COMBINE_G)[0] == "unmeasured"


def test_bob_starts_only_while_his_watch_and_the_close_fit_the_budget():
    import x483_options as D
    assert D.BUDGET_S - L.OBS_S - L.CLOSE_RESERVE_S <= 210.0
    for name in L.PROFILES:
        import tomllib
        with open(os.path.join(REPO, "testing", "profiles", name + ".toml"), "rb") as fh:
            assert tomllib.load(fh)["server"]["timeout"] == L.SERVER_TIMEOUT_S


def test_grade_track():
    rows = _line_rows()
    for r in rows:
        r["health"] = r.get("drain.target", 100.0)
    v, o = L.grade_track(rows, 3)
    assert v == "as_predicted" and o["max_gap"] == 0.0
    lag = copy.deepcopy(rows)
    lag[30]["health"] += 6e-4                                                   # health trailing its target
    assert L.grade_track(lag, 3)[0] == "falsified"
    assert L.grade_track(rows[:20], 3)[0] == "unmeasured"
    assert L.grade_track(rows, None)[0] == "unmeasured"


def test_rate_and_combine_read_only_their_masks():
    rows = _rate_rows()
    rows.append(dict(rows[-1], s=99, age=rows[-1]["age"] + 0.02, **{"drain.mask": 4, "drain.rate": 2.857142857142857}))
    assert L.grade_rate(rows)[0] == "as_predicted"                              # beriberi alone has no floor
    c = _comb_rows()
    for r in c:
        r["drain.mask"] = 5
    extra = dict(c[-1], s=99, age=c[-1]["age"] + 0.02, **{"drain.mask": 7, "drain.target": 50.0})
    v, o = L.grade_combine(c + [extra], c[0]["age"] - 0.001)
    assert v == "as_predicted" and o["n_other_mask"] == 1
