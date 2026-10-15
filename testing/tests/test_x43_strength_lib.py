"""Offline tests of testing/experiments/x43_strength_lib.py (Plan 13 Tasks 19 to 22, runs x431 to x434): every grade with
a failing case, the kernel replay against the staged copy's kernel, the creation expectations against Task 2b's
reference and the kernel's own table, the pre-boot checks on the real repository and a real run layout, and each
session's body run against a fake world behind a fake bus, once as predicted and once per defect flag that must move
a grade off as_predicted.

The fake bus answers the harness's real reply shapes, read off the handlers' `@reply` lines
(testing/PZTestKit/PZTestKit/42/media/lua): lua.read {ok, side, root, n, values, tables, types, missing}; record.set
{ok, side, user, path, key, keyType, before, beforeType, after, afterType}; perk.xp {perk, user, side, xp, level,
serverWorldAge}; xp.grant {ok, perk, amount, side, xpBefore, xpAfter, levelBefore, levelAfter}; bt.stored {ok, loaded,
stored, apiVersion, perk}; stats.get {weight, traitList, ..., worldAge, wall}; lua.call {ok, side, path, nargs, r1};
lua.callm {ok, side, path, method, nargs, r1}; lua.global {side, name, resolved, type, value}; moddata.set {user, key,
value, side, keyCount, keys, serverWorldAge}; health.reduce {ok, side, requested, before, after, health, parts};
creation.picks {ok, armed, picks}; trait.def {ok, side, trait, field, cost, free, xpBoosts, xpBoostsRead, exclusive,
granted, label, description}; witness.chain {ok, value, hops}; time.snapshot {worldAge, hour, minutes, mult, trueMult,
wall}; time.multiplier a string; players a list of usernames or {}.
"""
import math
import os
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                                  # testing/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))
sys.path.insert(0, HERE)                                                   # testing/tests (kernel.strength_level)

import x43_strength_lib as L          # noqa: E402
import xlib as X                      # noqa: E402

REPO = L.REPO
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
GAME_DIR = r"D:\SteamLibrary\steamapps\common\ProjectZomboid"


@pytest.fixture(scope="module")
def kern():
    return L.Kernel(SHARED)


def fresh_out():
    return {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {}, "readings": {},
            "world_changes": {"left_in_place": []}}


def flat(t, prefix=""):
    """A lupa body table flattened as the lib's record read flattens it."""
    out = {}
    for k in list(t.keys()):
        v = t[k]
        key = f"{prefix}{k}"
        if hasattr(v, "keys"):
            for kk in list(v.keys()):
                vv = v[kk]
                if hasattr(vv, "keys"):
                    for k3 in list(vv.keys()):
                        out[f"{key}.{kk}.{k3}"] = vv[k3]
                else:
                    out[f"{key}.{kk}"] = vv
        else:
            out[key] = v
    return out


MODEL_P = None


def model(kern):
    D = kern.K.strength.DEFAULTS
    return {"R": float(D.R), "M5": float(D.M5), "Fnm": float(D.Fnm), "b": float(D.b)}


# ---------------------------------------------------------------- pure helpers
def test_norm_and_bands():
    assert L.norm("base:very underweight") == L.norm("VERY_UNDERWEIGHT") == L.norm("VeryUnderweight")
    assert [L.band_of(n) for n in range(11)] == ["weak", "weak", "feeble", "feeble", "feeble", None, "stout",
                                                 "stout", "stout", "strong", "strong"]


def test_level_inverse_and_shown(kern):
    M = model(kern)
    for lv in (1.0, 3.75, 5.0, 9.5, 12.3):
        F = L.f_of_level(lv, 1.07, 1.03, M)
        assert abs(L.level_of(F, 1.07, 1.03, M) - lv) < 1e-9
        assert abs(kern.level(F, 1.07, 1.03, kern.K.strength.DEFAULTS) - lv) < 1e-9
    assert L.shown(9.5) == (9, 0.5) and L.shown(12.3)[0] == 10 and L.shown(12.3)[1] == 0.0
    assert L.pin_xp(9, 0.5) == 412500.0 and L.pin_xp(10, 0.0) == 337500.0


def test_mastery_xp_reads_the_ladder():
    cum = {10: 0, 11: 180000, 12: 390000, 13: 630000, 14: 900000, 15: 1200000}
    assert abs(L.mastery_xp(12.3, cum) - (390000 + 0.3 * 240000)) < 1e-6
    assert L.mastery_xp(16.0, cum) == 1200000
    assert L.mastery_xp(10.5, cum) == 90000


def test_body_paths_fit_lua_read():
    a, b = L.body_paths()
    assert len(a) <= 64 and len(b) <= 64 and len(set(a + b)) == len(a + b)


# ---------------------------------------------------------------- the creation expectations
def test_profession_table_reads_the_install():
    if not os.path.isdir(GAME_DIR):
        pytest.skip("no install")
    t = L.profession_table(GAME_DIR)
    assert t["unemployed"] == (8, 0) and t["farmer"] == (0, 1) and t["fitnessinstructor"] == (-6, 1)
    assert L.profession_id("base:unemployed") == "unemployed" and L.profession_id("Unemployed") == "unemployed"


DEFS = {"strong": {"cost": 10, "exclusive": ["base:feeble", "base:stout", "base:weak"]},
        "stout": {"cost": 6, "exclusive": ["feeble", "strong", "weak"]},
        "feeble": {"cost": -6, "exclusive": ["stout", "strong", "weak", "underweight", "very underweight"]},
        "weak": {"cost": -10, "exclusive": ["feeble", "stout", "strong", "underweight", "very underweight"]},
        "obese": {"cost": -10, "exclusive": ["athletic", "emaciated", "fit", "light eater", "very underweight",
                                             "underweight", "overweight", "weight loss"]},
        "overweight": {"cost": -6, "exclusive": ["athletic", "fit", "emaciated", "very underweight", "underweight",
                                                 "obese", "weight loss"]},
        "underweight": {"cost": -6, "exclusive": ["obese", "very underweight", "overweight", "weak", "feeble"]},
        "veryunderweight": {"cost": -10, "exclusive": ["athletic", "obese", "overweight", "underweight", "weak",
                                                       "feeble"]},
        "thickskinned": {"cost": 8, "exclusive": ["thin skinned"]}, "keenhearing": {"cost": 6, "exclusive": []},
        "fasthealer": {"cost": 6, "exclusive": ["slow healer"]}, "brave": {"cost": 4, "exclusive": []},
        "crafty": {"cost": 3, "exclusive": []}, "dextrous": {"cost": 2, "exclusive": []},
        "speeddemon": {"cost": 1, "exclusive": []}}


@pytest.mark.parametrize("lab, want", [("a", []), ("b", []), ("c", []), ("d", ["obese", "thickskinned", "fasthealer"]),
                                       ("e", ["weak"])])
def test_expected_strips_follow_the_cost_order(lab, want):
    picks = dict(L.CASES)[lab]
    stripped, kept = L.expect_strips(picks, DEFS, 8, 0, 1)
    assert stripped == want
    assert set(kept) | set(stripped) == {L.norm(p) for p in picks}


def test_expected_strips_penalty_and_unread_cost():
    # penalty 4 (n - 1): two kept negatives cost one point more, so the budget strips one more pick in (d)
    s, _k = L.expect_strips(dict(L.CASES)["d"], DEFS, 8, 0, 4)
    assert s[:3] == ["obese", "thickskinned", "fasthealer"]
    bad = dict(DEFS)
    bad["brave"] = {"cost": None}
    assert L.expect_strips(dict(L.CASES)["d"], bad, 8, 0, 1) == (None, None)


@pytest.mark.parametrize("muscle, weight, prof", [(None, None, 0), ("STRONG", "OVERWEIGHT", 0),
                                                  ("STRONG", "VERY_UNDERWEIGHT", 0), ("FEEBLE", "OVERWEIGHT", 0),
                                                  (None, "UNDERWEIGHT", 0), (None, None, 1), ("STOUT", "OBESE", 1)])
def test_expected_body_equals_the_kernel_table(kern, muscle, weight, prof):
    # the lib is frozen at the build x431-x433 ran on (the plan's Task 9 fat table); Plan 13 Task 10b (Angus,
    # 2026-10-15) scales the kernel's fat start by the start lean over the average's and moves Obese from FMI 12.5
    # to 10.5, so the kernel's fm is checked against that rule and the lib's against its own frozen table
    kept = [x.lower().replace("_", "") for x in (muscle, weight) if x]
    e = L.expect_body(kept, prof)
    s = kern.K.body.create(muscle, weight, kern.K.strength.DEFAULTS, 1, prof)
    for k in ("lm", "F0", "Fc", "Pk", "N0"):
        assert abs(float(s[k]) - e[k]) < 1e-9, k
    H2 = L.H2
    if weight in ("UNDERWEIGHT", "VERY_UNDERWEIGHT"):
        assert abs(float(s["fm"]) - e["fm"]) < 1e-9
    else:
        w = weight.lower() if weight else None
        fmi10b = {None: 4.5, "overweight": 7.5, "obese": 10.5}[w]
        assert abs(float(s["fm"]) - fmi10b * H2 * e["lm"] / (18.0 * H2)) < 1e-9
        assert abs(e["fm"] - L.FAT_FMI[w] * H2) < 1e-12
        assert L.FAT_FMI == {None: 4.5, "overweight": 7.5, "obese": 12.5}


def test_the_thin_picks_land_feeble():
    for kept, lv in ((["strong", "veryunderweight"], 3.83), (["underweight"], 3.75), (["veryunderweight"], 2.89)):
        e = L.expect_body(kept, 0)
        assert abs(e["level"] - lv) < 0.01 and e["band"] == "feeble"


# ---------------------------------------------------------------- the grades
def test_grade_sentinel():
    assert L.grade_sentinel({"keys": 4, "wrapper": "function", "answered": True})[0] == "as_predicted"
    assert L.grade_sentinel({"keys": None, "wrapper": None, "answered": True})[0] == "falsified"
    assert L.grade_sentinel({"keys": 4, "wrapper": "table", "answered": True})[0] == "falsified"
    assert L.grade_sentinel({})[0] == "unmeasured"


def w12(M, **kw):
    F = L.f_of_level(12.3, 1.0, 1.0, M)
    cum = {10: 0, 11: 180000, 12: 390000, 13: 630000}
    lv = L.level_of(F, 1.0, 1.0, M)
    w = {"model": M, "after": {"lm": F, "N0": 1.0, "T": 1.0}, "cum": cum, "wrote": True, "bt_loaded": True,
         "level": 10, "xp": 337500.0, "stored": L.mastery_xp(lv, cum), "mirror": round(lv, 2)}
    w.update(kw)
    return w


def test_grade_write12(kern):
    M = model(kern)
    assert L.grade_write12(w12(M))[0] == "as_predicted"
    for bad in ({"level": 9}, {"xp": 37500.0}, {"stored": 390000.0}, {"mirror": 12.0}):
        assert L.grade_write12(w12(M, **bad))[0] == "falsified", bad
    assert L.grade_write12(w12(M, wrote=False))[0] == "unmeasured"
    assert L.grade_write12(w12(M, bt_loaded=False))[0] == "unmeasured"


def test_grade_grant():
    ok = {"sig0": 10.0, "sig1": 360.0, "cap0": 4, "cap1": 5, "level": 10, "day0": 3, "day1": 3}
    assert L.grade_grant(ok, 0.35)[0] == "as_predicted"
    assert L.grade_grant(dict(ok, sig1=1010.0), 0.35)[0] == "falsified"
    assert L.grade_grant(dict(ok, level=9), 0.35)[0] == "falsified"
    assert L.grade_grant(dict(ok, cap1=4), 0.35)[0] == "unmeasured"
    assert L.grade_grant(dict(ok, day1=4), 0.35)[0] == "unmeasured"


def test_grade_rust():
    ok = {"ign0": 1, "ign1": 2, "grd0": 0, "grd1": 1, "level0": 10, "level1": 10}
    v, o = L.grade_rust(ok)
    assert v == "as_predicted" and o["outermost"].startswith("the mod's guard")
    assert L.grade_rust(dict(ok, level1=9))[0] == "falsified"
    assert L.grade_rust(dict(ok, ign1=1))[0] == "unmeasured"
    assert L.grade_rust(dict(ok, level0=9))[0] == "unmeasured"


def test_grade_write95():
    ok = {"wrote": True, "level": 9, "xp": 412500.0, "server_traits": ["strong"], "client_traits": ["strong"],
          "pair_gap_s": 0.2}
    assert L.grade_write95(ok)[0] == "as_predicted"
    for bad in ({"level": 10}, {"xp": 337500.0}, {"client_traits": ["stout"]}, {"server_traits": ["strong", "stout"]}):
        assert L.grade_write95(dict(ok, **bad))[0] == "falsified", bad
    assert L.grade_write95(dict(ok, pair_gap_s=3.0))[0] == "unmeasured"
    assert L.grade_write95(dict(ok, client_traits=None))[0] == "unmeasured"


def rec(day=5, lm=52.0):
    b = {"dayIndex": day, "grace": 0, "Pk": lm, "lm": lm, "fm": 13.0, "lx": 0.0}
    for r in L.RING_KEYS:
        for i in range(1, 8):
            b[f"{r}.{i}"] = float(i)
    for i in range(1, 8):
        b[f"bandWeek.{i}.1"], b[f"bandWeek.{i}.2"] = 0, 0
    return b


def test_grade_gap_and_xp():
    o = {"rejoined": True, "gap_h": 80.0, "pre": rec(), "away": rec(), "first": rec(),
         "xp_pre": {"xp": 37500.0, "level": 5}, "xp_first": {"xp": 37500.0, "level": 5}}
    assert L.grade_gap(o)[0] == "as_predicted"
    assert L.grade_gap(dict(o, first=rec(day=6)))[0] == "falsified"
    assert L.grade_gap(dict(o, first=rec(lm=52.1)))[0] == "falsified"
    assert L.grade_gap(dict(o, gap_h=30.0))[0] == "unmeasured"
    assert L.grade_xp(o)[0] == "as_predicted"
    assert L.grade_xp(dict(o, xp_first={"xp": 37499.0, "level": 5}))[0] == "falsified"


def shifted(b):
    a = dict(b)
    a["dayIndex"] = b["dayIndex"] + 1
    for r in L.RING_KEYS:
        for i in range(1, 7):
            a[f"{r}.{i}"] = b[f"{r}.{i + 1}"]
        a[f"{r}.7"] = 99.0
    return a


def test_grade_close():
    first = rec()
    after = shifted(first)
    o, b = {"first": first}, {"after": after, "hold": after, "crossed": True, "days0": 10, "days1": 11}
    assert L.grade_close(o, b)[0] == "as_predicted"
    assert L.grade_close(o, dict(b, days1=12))[0] == "falsified"
    assert L.grade_close(o, dict(b, hold=shifted(after)))[0] == "falsified"
    twice = shifted(after)
    twice["dayIndex"] = first["dayIndex"] + 1
    assert L.grade_close(o, dict(b, after=twice, hold=twice))[0] == "falsified"
    assert L.grade_close(o, dict(b, crossed=False))[0] == "unmeasured"


def case(kept=("strong", "overweight"), **kw):
    e = L.expect_body(list(kept), 0)
    body = {k: e[k] for k in ("lm", "fm", "F0", "Fc", "Pk", "N0")}
    body["lx"] = 0.0
    mass = e["lm"] + e["fm"]
    traits = [t for t in (e["band"], e["weight"]) if t]
    pair = {"server_stats": {"weight": mass, "traitList": list(traits)},
            "client_stats": {"weight": mass, "traitList": list(traits)},
            "server_xp": {"level": e["native"]}, "client_xp": {"level": e["native"]}, "gap_s": 0.3}
    c = {"landed": True, "expect": e, "body": body, "pair": pair, "want_stripped": []}
    c.update(kw)
    return c


def test_grade_case_body_and_state():
    assert L.grade_case_body(case())[0] == "as_predicted"
    c = case()
    c["body"]["lm"] += 1e-6
    assert L.grade_case_body(c)[0] == "falsified"
    assert L.grade_case_body(case(landed=False))[0] == "unmeasured"
    assert L.grade_case_state(case())[0] == "as_predicted"
    c = case()
    c["pair"]["client_xp"]["level"] = 5
    assert L.grade_case_state(c)[0] == "falsified"
    c = case()
    c["pair"]["server_stats"]["traitList"] = ["strong", "overweight", "obese"]
    assert L.grade_case_state(c)[0] == "falsified"
    c = case(kept=("veryunderweight", "strong"))
    assert c["expect"]["band"] == "feeble"
    assert L.grade_case_state(c)[0] == "as_predicted"
    c["pair"]["client_stats"]["traitList"] = ["strong", "veryunderweight"]
    assert L.grade_case_state(c)[0] == "falsified"
    c = case(want_stripped=["obese"])
    c["pair"]["client_stats"]["traitList"] = c["pair"]["client_stats"]["traitList"] + ["obese"]
    assert L.grade_case_state(c)[0] == "falsified"
    c = case()
    c["pair"]["gap_s"] = 2.0
    assert L.grade_case_state(c)[0] == "unmeasured"


def test_strips_by_case_and_grade():
    lines = ["[NutritionRevamp] creation: bob muscle=nil weight=nil prof=0",
             "[NutritionRevamp] creation: bob loses obese (excluded by overweight)",
             "[NutritionRevamp] creation: bob loses thick skinned (over the point total)",
             "[NutritionRevamp] creation: bob loses fast healer (over the point total)",
             "[NutritionRevamp] creation: bob muscle=FEEBLE weight=OVERWEIGHT prof=0"]
    cr = L.strips_by_case(lines)
    assert cr[0]["strips"] == [] and cr[1]["strips"] == ["obese", "thickskinned", "fasthealer"]
    c = {"landed": True, "want_stripped": ["obese", "thickskinned", "fasthealer"]}
    assert L.grade_case_strips(c, cr[1])[0] == "as_predicted"
    assert L.grade_case_strips(dict(c, want_stripped=["obese", "fasthealer", "thickskinned"]), cr[1])[0] == "falsified"
    assert L.grade_case_strips(c, None)[0] == "unmeasured"


def pre_body(kern, muscle=None, T=1.0, ageH=100.5):
    D = kern.K.strength.DEFAULTS
    b = kern.K.body.new(kern.K.body.create(muscle, None, D, 1, 0), 1, ageH)
    b.T = T
    f = flat(b)
    f = {k: v for k, v in f.items() if not k.startswith("trail")}
    return f


def make_post(kern, P, pre, S, p, E, tdee, drift_lm=0.0, drift_T=0.0):
    w = pre["fm"] + pre["lm"] + pre["lx"]
    r = kern.day(pre, S, p, E, tdee, 0.0, P)
    post = dict(pre)
    post.update({"lm": r["lm"] + drift_lm, "T": r["T"] + drift_T, "S": S, "p7.7": p * w, "eb7.7": E, "N0": pre["N0"]})
    return post


def test_params_read_the_profile_options(kern):
    P = kern.params({"StrengthTimeScale": 30.0, "StrengthIncidentalWeight": 1.0})
    assert float(P.ts) == 30.0 and float(P.incidental) == 1.0 and float(P.xpPerSet) == 360.0


def test_replay_and_close_grade(kern):
    P = kern.params({"StrengthTimeScale": 30.0, "StrengthIncidentalWeight": 1.0})
    pre = pre_body(kern)
    pre["eeDay"] = 1900.0
    S = 2.0 * 20 / 7
    post = make_post(kern, P, pre, S, 2.0, 255.0, 1900.0)
    c = {"closed": True, "pre": pre, "post": post}
    c["replay"], c["inputs"] = L.replay_close(kern, P, pre, post)
    assert c["replay"]["tdee_sensitive"] is False
    assert c["replay"]["lm"] > pre["lm"] and c["replay"]["T"] > 1.0
    assert L.grade_growth_close(c)[0] == "as_predicted"
    for dl, dt in ((2e-6, 0.0), (0.0, 2e-9)):
        bad = make_post(kern, P, pre, S, 2.0, 255.0, 1900.0, dl, dt)
        cb = {"closed": True, "pre": pre, "post": bad}
        cb["replay"], cb["inputs"] = L.replay_close(kern, P, pre, bad)
        assert L.grade_growth_close(cb)[0] == "falsified"
    grown = dict(pre, lm=pre["lm"] + 2.0)             # status above 0: the balance gate below 1 reads tdee
    small = make_post(kern, P, grown, S, 2.0, 60.0, 1900.0)
    cs = {"closed": True, "pre": grown, "post": small}
    cs["replay"], cs["inputs"] = L.replay_close(kern, P, grown, small)
    assert L.grade_growth_close(cs)[0] == "unmeasured"
    assert L.grade_growth_close({"closed": False})[0] == "unmeasured"


def test_grade_growth_level(kern):
    M = model(kern)
    F = L.f_of_level(6.2, 1.0, 1.05, M)
    c = {"closed": True, "post": {"lm": F, "N0": 1.0, "T": 1.05}, "xp": {"level": 6},
         "stats": {"traitList": ["stout"]}}
    assert L.grade_growth_level(c, M)[0] == "as_predicted"
    assert L.grade_growth_level(dict(c, xp={"level": 5}), M)[0] == "falsified"
    assert L.grade_growth_level(dict(c, stats={"traitList": []}), M)[0] == "falsified"
    assert L.grade_growth_level(dict(c, stats=None), M)[0] == "unmeasured"


# ---------------------------------------------------------------- the pre-boot checks
def test_harness_markers_are_in_the_repository():
    found, ok = L.harness_markers_ok()
    assert ok, found


def test_deployed_marker_check_on_a_run_layout():
    with tempfile.TemporaryDirectory() as d:
        for fname, rel in L.HARNESS_FILES.items():
            side = rel.split("/")[-2]
            dst = os.path.join(d, "server", "Zomboid", "mods", "PZTestKit", "42", "media", "lua", side, fname)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(os.path.join(REPO, rel), encoding="utf-8", errors="replace") as fh, \
                    open(dst, "w", encoding="utf-8") as out:
                out.write(fh.read())
        dm, ok = X.deployed_marker_check(d, list(L.HARNESS_MARKERS), L.HARNESS_MARKERS)
        assert ok, dm
        p = os.path.join(d, "server", "Zomboid", "mods", "PZTestKit", "42", "media", "lua", "server",
                         "PZTestKit_Server.lua")
        with open(p, "w", encoding="utf-8") as out:
            out.write("-- emptied")
        assert X.deployed_marker_check(d, list(L.HARNESS_MARKERS), L.HARNESS_MARKERS)[1] is False


def test_profiles_load_and_boot_the_staged_copy():
    from pzt import profile
    want = {"x43-beyondten": ("default", ["admin"]), "x43-offline": ("default", ["admin"]),
            "x43-creation": ("two", ["admin", "bob"]), "x43-growth": ("default", ["admin"])}
    for name, (fixture, users) in want.items():
        path = os.path.join(REPO, "testing", "profiles", name + ".toml")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        assert 'path = "' + L.STAGE_MOD + '"' in text, name
        assert "Nutrition = false" in text and "DayLength = 1" in text, name
        assert f'fixture = "{fixture}"' in text, name
        assert '"value": "1.0.0"' in text, name
    with open(os.path.join(REPO, "testing", "profiles", "x43-growth.toml"), encoding="utf-8") as fh:
        t = fh.read()
    assert "StrengthTimeScale = 30" in t and "StrengthIncidentalWeight = 1" in t
    with open(os.path.join(REPO, "testing", "profiles", "x43-beyondten.toml"), encoding="utf-8") as fh:
        assert 'workshop_id = "3765241705"' in fh.read()


def test_drivers_name_their_own_prefix_and_profile():
    for drv, prefix, prof, task in (("x431_beyondten.py", "x431", "x43-beyondten", "19"),
                                    ("x432_offline.py", "x432", "x43-offline", "20"),
                                    ("x433_creation.py", "x433", "x43-creation", "21"),
                                    ("x434_growth.py", "x434", "x43-growth", "22")):
        with open(os.path.join(REPO, "testing", "experiments", drv), encoding="utf-8") as fh:
            text = fh.read()
        assert f'PREFIX = "{prefix}"' in text and f'PROFILE = "{prof}"' in text and f'TASK = "{task}"' in text, drv


# ---------------------------------------------------------------- the fake world
class FakeClient:
    def __init__(self, user):
        self.username = user
        self.seen = {}
        self.alive = True

    def quit(self):
        self.alive = False
        return 0


class World:
    """A minimal server: one game clock, one record per user, the Strength level write, the day close through the
    real kernel, BeyondTen's park and stored XP, the rust pass and the creation handler. Flags break one thing each."""

    def __init__(self, kern, flags=None, user="admin", hour=8.0, bt=True):
        self.k = kern
        self.f = flags or {}
        self.user = user
        self.now = 1000.0
        self.age = 24.0 * 10 + hour
        self.mult = 1.0
        self.online = {user}
        self.bt = bt
        self.D = kern.K.strength.DEFAULTS
        self.P = kern.params({"StrengthTimeScale": 30.0, "StrengthIncidentalWeight": 1.0}) if self.f.get("growth") \
            else kern.params(None)
        self.body = pre_body(kern, ageH=self.age)
        self.body["levelDue"] = False
        self.body["wroteL"] = 5
        self.body["eeDay"] = 0.0
        self.level, self.xp, self.stored = 5, 37500.0, 0.0
        self.counters = {"levelWrites": 0, "guarded": 0, "ignored": 0, "created": 0, "runs": 5, "days": 0,
                         "captures": 0}
        self.traits = []
        self.timer = None
        self.last_min = math.floor(self.age * 60)
        self.last10 = math.floor(self.age * 6)
        self.gapped = False
        self.logs = []
        self.armed = None
        self.dead = False
        self.prof = "base:unemployed"

    # -- the clock
    def clock(self):
        return self.now

    def sleep(self, s):
        end = self.now + max(0.0, s)
        while self.now < end:
            dt = min(0.05, end - self.now)
            self.now += dt
            self.age += dt * self.mult / 37.5
            self.tick()

    def model(self):
        return {"R": float(self.P.R), "M5": float(self.P.M5), "Fnm": float(self.P.Fnm), "b": float(self.P.b)}

    def tick(self):
        m = math.floor(self.age * 60)
        while self.last_min < m:
            self.last_min += 1
            if self.user in self.online:
                self.minute()
        t = math.floor(self.age * 6)
        while self.last10 < t:
            self.last10 += 1
            if self.timer is not None and self.user in self.online:
                self.timer = None
                self.counters["ignored"] += 1
                if self.level == 10 and self.body["wroteL"] == 10 and not self.f.get("rust_drops"):
                    self.counters["guarded"] += 1
                else:
                    self.level = 9

    def minute(self):
        b = self.body
        if self.gapped:
            self.gapped = False
            b["wday"] = math.floor(self.age / 24.0)
            b["lastAgeH"] = self.age
            return
        b["eeDay"] = b.get("eeDay", 0.0) + 1.4
        b["ebDay"] = b.get("ebDay", 0.0) - 1.4
        if math.floor(self.age / 24.0) > b["wday"]:
            b["wday"] = math.floor(self.age / 24.0)
            self.close()
        b["lastAgeH"] = self.age
        if b.get("levelDue"):
            self.write()

    def close(self):
        b = self.body
        sig = [b[f"sig7.{i}"] for i in range(2, 8)] + [b["sigDay"]]
        for i in range(1, 8):
            b[f"sig7.{i}"] = sig[i - 1]
        b["sigDay"] = 0.0
        S = sum(sig) / float(self.P.xpPerSet)
        w = b["fm"] + b["lm"] + b["lx"]
        tdee = max(b["eeDay"], self.k.ree(b["lm"]))
        r = self.k.day(b, S, b["pDay"] / w, b["ebDay"], tdee, 0.0, self.P)
        b["lm"] = r["lm"] + (1e-4 if self.f.get("drift") else 0.0)
        b["T"], b["lx"], b["fm"] = r["T"], r["lx"], r["fm"]
        b["S"] = S
        for key, v in (("eb7", b["ebDay"]), ("p7", b["pDay"]), ("mass7", b["fm"] + b["lm"] + b["lx"])):
            ring = [b[f"{key}.{i}"] for i in range(2, 8)] + [v]
            for i in range(1, 8):
                b[f"{key}.{i}"] = ring[i - 1]
        for k in ("eeDay", "ebDay", "pDay", "inDay", "alcDay"):
            b[k] = 0.0
        b["dayIndex"] += 1
        if self.f.get("double_close"):
            b["dayIndex"] += 1
        self.counters["days"] += 1
        b["levelDue"] = True

    def write(self):
        b = self.body
        lv = L.level_of(b["lm"], b["N0"], b["T"], self.model())
        n, frac = L.shown(lv)
        self.level = n
        if n >= 10 and self.bt:
            self.xp = L.PARK_XP
            self.stored = L.mastery_xp(lv, self.cum())
        else:
            if self.bt:
                self.stored = 0.0
            self.xp = L.pin_xp(n, frac)
        band = L.band_of(n)
        self.traits = [t for t in self.traits if t not in L.MUSCLE] + ([band] if band else [])
        if self.f.get("no_band"):
            self.traits = [t for t in self.traits if t not in L.MUSCLE]
        b["wroteL"] = n
        b["levelDue"] = False
        self.counters["levelWrites"] += 1

    def cum(self):
        return {10: 0, 11: 180000, 12: 390000, 13: 630000, 14: 900000, 15: 1200000}

    # -- reads
    def G(self, path):
        P = self.P
        tab = {f"{L.STR_STATS}.levelWrites": self.counters["levelWrites"],
               f"{L.STR_STATS}.guarded": self.counters["guarded"],
               f"{L.STR_XP}.ignored": self.counters["ignored"],
               f"{L.STR_XP}.captures": self.counters["captures"],
               f"{L.NR}.server.minute.stats.runs": self.counters["runs"],
               f"{L.NR}.server.metabolism.stats.days": self.counters["days"],
               f"{L.NR}.server.creation.stats.created": self.counters["created"],
               "SandboxVars.CharacterFreePoints": 0, "SandboxVars.NegativeTraitsPenalty": 1,
               "SandboxVars.Nutrition": False, "SandboxVars.DayLength": 1,
               f"{L.NR}.client.received": int(self.now), "TK.picksFired.count": 1}
        for k in ("R", "M5", "Fnm", "b", "incidental", "xpPerSet", "ts", "k"):
            tab[f"{L.OPT_STR}.{k}"] = float(P[k])
        lv = L.level_of(self.body["lm"], self.body["N0"], self.body["T"], self.model())
        tab[f"{L.NR}.client.mirror.body_level"] = round(lv, 2) + (0.5 if self.f.get("mirror_off") else 0.0)
        return tab.get(path)

    def lread(self, args, side):
        parts = args.split()
        root, paths = parts[0], parts[1:]
        out = {"ok": True, "side": side, "root": root, "n": len(paths), "values": {}, "tables": {}, "types": {},
               "missing": {}}
        if root.startswith("record:"):
            for p in paths:
                v = self.body.get(p[5:]) if p.startswith("body.") else None
                if v is None:
                    out["missing"][p] = "nil"
                else:
                    out["values"][p] = v
            return out
        for p in paths:
            if p == "NR_StrengthGuardInstalled":
                if self.f.get("no_answer"):
                    return {"ok": False, "side": side, "root": root, "error": "fake: no answer"}
                if not self.f.get("no_guard"):
                    out["tables"][p] = 4
                continue
            if p in ("NR_StrengthGuardInstalled.wrapper", "NR_StrengthGuardInstalled.orig",
                     "xpUpdate.checkForLosingLevel", "xpUpdate._BeyondTenB42OriginalCheckForLosingLevel"):
                if not self.f.get("no_guard"):
                    out["types"][p] = "function"
                continue
            v = self.G(p)
            if v is None:
                out["missing"][p] = "nil"
            else:
                out["values"][p] = v
        return out

    def stats(self, side):
        mass = self.body["fm"] + self.body["lm"] + self.body["lx"]
        tl = list(self.traits)
        if side != "server" and self.f.get("client_stale"):
            tl = [t for t in tl if t not in L.MUSCLE] + ["stout"]
        return {"weight": mass, "traitList": tl, "worldAge": self.age, "wall": self.now}

    def ask(self, node, cmd, args="", timeout=30):
        self.sleep(0.05)
        a = args.split()
        side = "server" if node == "server" else "client"
        if cmd == "ping":
            return "pong"
        if cmd == "players":
            return sorted(self.online) if self.online else {}
        if cmd == "time.snapshot":
            return {"worldAge": self.age, "hour": int(self.age % 24), "minutes": 0, "mult": self.mult,
                    "trueMult": self.mult, "wall": self.now}
        if cmd == "time.multiplier":
            self.mult = float(a[0])
            return f"mult={self.mult} eff={self.mult}"
        if cmd == "lua.read":
            return self.lread(args, node)
        if cmd == "lua.global":
            return {"side": side, "name": a[0], "resolved": self.bt, "type": "number", "value": 1}
        if cmd == "lua.call":
            if a[0] == "BeyondTen.GetTotalMasteryCost":
                return {"ok": True, "side": side, "path": a[0], "nargs": 2, "r1": self.cum().get(int(a[2]))}
            return {"ok": True, "side": side, "path": a[0], "nargs": len(a) - 1, "r1": True}
        if cmd == "record.set":
            key = a[1][5:]
            raw = a[2]
            v = True if raw == "true" else False if raw == "false" else float(raw)
            before = self.body.get(key)
            self.body[key] = v
            return {"ok": True, "side": side, "user": a[0], "path": a[1], "key": key, "before": before, "after": v}
        if cmd == "perk.xp":
            return {"perk": "Strength", "user": self.user, "side": side, "xp": self.xp, "level": self.level}
        if cmd == "bt.stored":
            return {"ok": True, "loaded": self.bt, "stored": self.stored if self.bt else None, "apiVersion": 1}
        if cmd == "xp.grant":
            amt = float(a[2])
            x0 = self.xp
            if self.xp < L.CAP_XP:
                self.xp += amt
                self.body["sigDay"] += amt * float(self.P.incidental) * (2.0 if self.f.get("double_sig") else 1.0)
                self.counters["captures"] += 1
                if self.level >= 10 and self.bt:
                    self.xp = L.PARK_XP
            return {"ok": True, "perk": "Strength", "amount": amt, "side": side, "xpBefore": x0, "xpAfter": self.xp,
                    "levelBefore": self.level, "levelAfter": self.level}
        if cmd == "moddata.set":
            if a[1] == "strengthUpTimer" and a[2] == L.RUST_TIMER and not self.f.get("no_rust"):
                self.timer = True
            return {"user": a[0], "key": a[1], "value": a[2], "side": side, "keyCount": 3, "keys": []}
        if cmd == "stats.get":
            return self.stats(side)
        if cmd == "witness.chain":
            ch = a[-1]
            if ch == "isDead":
                return {"ok": True, "value": "true" if self.dead else "false"}
            if ch.startswith("getDescriptor.getCharacterProfession"):
                return {"ok": True, "value": self.prof}
            return {"ok": False, "failedAt": 1}
        if cmd == "health.reduce":
            self.dead = True
            return {"ok": True, "side": side, "requested": 110, "before": 100, "after": 0}
        if cmd == "lua.callm":
            if a[1] == "accept":
                self.create()
            if a[1] == "getIsVisible":
                return {"ok": True, "side": side, "path": a[0], "method": a[1], "r1": a[0].startswith(
                    ("ISPostDeathUI", "CharacterCreationMain"))}
            return {"ok": True, "side": side, "path": a[0], "method": a[1], "r1": True}
        if cmd == "creation.picks":
            self.armed = list(a)
            return {"ok": True, "armed": True, "picks": list(a)}
        if cmd == "trait.def":
            d = DEFS.get(L.norm(a[0]))
            return {"ok": True, "side": side, "trait": a[0], "cost": d["cost"], "exclusive": d["exclusive"],
                    "free": False}
        return {"error": f"fake: unknown {cmd}"}

    def create(self):
        picks = self.armed or []
        self.armed = None
        self.dead = False
        stripped, kept = L.expect_strips(picks, DEFS, 8, 0, 1)
        if self.f.get("list_order"):
            stripped = list(reversed(stripped))
        e = L.expect_body(kept, 0)
        self.body.update({k: e[k] for k in ("lm", "fm", "F0", "Fc", "Pk", "N0")})
        self.body["lx"] = 0.0
        self.level = e["native"]
        self.traits = [t for t in (e["band"], e["weight"]) if t]
        if self.f.get("keep_strip") and stripped:
            self.traits.append(stripped[0])
        for s in stripped:
            self.logs.append(f"[NutritionRevamp] creation: {self.user} loses {s} (why)")
        self.logs.append(f"[NutritionRevamp] creation: {self.user} muscle={e['muscle']} weight={e['weight']} prof=0")
        self.counters["created"] += 1


def run_session(kern, task, flags=None, user="admin", hour=8.0):
    w = World(kern, flags, user=user, hour=hour, bt=(task == "19"))
    out = fresh_out()
    clients = {user: FakeClient(user)}
    if user != "admin":
        clients["admin"] = FakeClient("admin")
    xs = X.Xs(out, node=lambda side: side, clients=clients, ask=w.ask, budget_s=1e9, clock=w.clock, sleep=w.sleep)
    S = L.Sess(xs, user=user, cli="client" if user == "admin" else "client:bob", game_dir=GAME_DIR,
               shared_dir=SHARED)
    S.run_dir = "."

    def launch(sess, u, sub):
        w.online.add(u)
        w.gapped = True
        sess.xs.clients[u] = FakeClient(u)
        return {"restored": True, "ready_took": 30.0}
    S.launch = launch
    orig_quit = FakeClient.quit

    def quit_(c):
        w.online.discard(c.username)
        return orig_quit(c)
    for c in clients.values():
        c.quit = lambda c=c: quit_(c)
    body = {"19": S.t19_body, "20": S.t20_body, "21": S.t21_body, "22": S.t22_body}[task]
    S.body_run(body())
    if task == "19":
        S.t19_grade()
    elif task == "20":
        S.t20_grade()
    elif task == "21":
        if not os.path.isdir(GAME_DIR):
            S.D["S"]["prof_table"] = {"unemployed": (8, 0)}
        S.t21_grade(w.logs)
    else:
        S.t22_grade(kern=kern)
    assert not out["phase_errors"], out["phase_errors"]
    return {k: v["verdict"] for k, v in out["verdicts"].items()}, out


def test_t19_flow(kern):
    v, _o = run_session(kern, "19")
    assert set(v.values()) == {"as_predicted"}, v


@pytest.mark.parametrize("flag, name", [("mirror_off", "19_write12"), ("double_sig", "19_grant"),
                                        ("rust_drops", "19_rust"), ("client_stale", "19_write95"),
                                        ("no_guard", "19_sentinel")])
def test_t19_defects(kern, flag, name):
    v, _o = run_session(kern, "19", {flag: True})
    assert v[name] == "falsified", v


def test_t19_no_rust_is_unmeasured(kern):
    v, _o = run_session(kern, "19", {"no_rust": True})
    assert v["19_rust"] == "unmeasured"
    v, _o = run_session(kern, "19", {"no_answer": True})
    assert v["19_sentinel"] == "unmeasured"


def test_t20_flow(kern):
    v, o = run_session(kern, "20")
    assert set(v.values()) == {"as_predicted"}, (v, o["verdicts"])
    assert o["checks"]["OFF"]["gap_h"] >= L.AWAY_MIN_H


def test_t20_double_close(kern):
    v, _o = run_session(kern, "20", {"double_close": True})
    assert v["20_close"] == "falsified"


def test_t20_late_start_waits_out_the_boundary(kern):
    v, o = run_session(kern, "20", hour=23.5)
    assert set(v.values()) == {"as_predicted"} and "late_wait" in o["checks"]["OFF"]


def test_t21_flow(kern):
    v, o = run_session(kern, "21", user="bob")
    assert set(v.values()) == {"as_predicted"}, (v, {k: o["verdicts"][k]["observed"].get("why") for k in v})
    assert o["checks"]["Cd"]["want_stripped"] == ["obese", "thickskinned", "fasthealer"]


@pytest.mark.parametrize("flag, name", [("list_order", "21_d_strips"), ("keep_strip", "21_e_state")])
def test_t21_defects(kern, flag, name):
    v, _o = run_session(kern, "21", {flag: True}, user="bob")
    assert v[name] == "falsified", v


def test_t22_flow(kern):
    v, o = run_session(kern, "22", {"growth": True}, hour=6.0)
    assert set(v.values()) == {"as_predicted"}, (v, {k: o["verdicts"][k]["observed"].get("why") for k in v})
    assert all(f"22_close{k}" in v for k in (1, 2, 3)) and "22_close0" not in v
    d3 = o["checks"]["day3"]
    assert d3["post"]["lm"] > o["checks"]["day1"]["pre"]["lm"]


def test_t22_lead_in_close_and_defects(kern):
    v, _o = run_session(kern, "22", {"growth": True}, hour=15.0)
    assert "22_close0" in v and v["22_close0"] == "as_predicted"
    v, _o = run_session(kern, "22", {"growth": True, "drift": True}, hour=6.0)
    assert v["22_close1"] == "falsified"
    v, _o = run_session(kern, "22", {"growth": True, "no_band": True}, hour=6.0)
    assert "falsified" in {v[f"22_level{k}"] for k in (1, 2, 3)}
