"""Offline tests of testing/experiments/x43c_strength_lib.py (Plan 13 Task 22b, runs x435 and x436): every grade with a
failing case, the lib's Python mirrors of the kernel (heldLevel, pinXp, the ENERGY_AT rung) against the staged kernel,
the creation expectation against the kernel's own table, the pre-boot checks on the real repository, and each session's
body run against a fake world behind a fake bus, once as predicted and once per defect flag that must move a grade off
as_predicted.

The fake bus answers the harness's real reply shapes, read off the handlers' `@reply` lines
(testing/PZTestKit/PZTestKit/42/media/lua): lua.read {ok, side, root, n, values, tables, types, missing}; record.set
{ok, side, user, path, key, keyType, before, beforeType, after, afterType}; perk.xp {perk, user, side, xp, level,
serverWorldAge}; xp.grant {ok, perk, amount, side, xpBefore, xpAfter, levelBefore, levelAfter}; stats.get {weight,
traitList, ..., worldAge, wall}; stats.set {calories, ..., hunger, thirst, ..., applied}; lua.call {ok, side, path,
nargs, r1}; lua.callm {ok, side, path, method, nargs, r1}; health.reduce {ok, side, requested, before, after, health,
parts}; creation.picks {ok, armed, picks}; trait.def {ok, side, trait, field, cost, free, xpBoosts, xpBoostsRead,
exclusive, granted, label, description}; witness.chain {ok, value, hops}; time.snapshot {worldAge, hour, minutes, mult,
trueMult, wall}; time.multiplier a string; players a list of usernames or {}.

The kernel the lib's mirrors and sessions read is the shared folder of a git archive of PIN (CLAUDE.md section 5: a
grade or replay script broken at HEAD by a later mod change is never patched, it runs on a git archive of a build it
holds at): Plan 15 Task 9 removed the energy class (K.view.ENERGY_AT) the lib's energy rung and its client-level read
mirror, and PIN is the last build that carries it, the build these tests last passed on.
"""
import atexit
import io
import math
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))
sys.path.insert(0, HERE)

import test_x43_strength_lib as T     # noqa: E402
import x43c_strength_lib as L         # noqa: E402
import xlib as X                      # noqa: E402

REPO = L.REPO
GAME_DIR = T.GAME_DIR
PIN = "7c8725b3"          # Plan 15 Task 8 fix 1, the last build with K.view.ENERGY_AT (Plan 15 Task 9 removed it)
_PINNED = {}


def pinned_shared():
    """The shared Lua folder of a git archive of PIN, extracted once per session into a temporary folder."""
    if "dir" not in _PINNED:
        d = tempfile.mkdtemp(prefix="x43c-kernel-")
        atexit.register(shutil.rmtree, d, True)            # removed at the session's end (fix 1, review L7)
        data = subprocess.run(["git", "-C", REPO, "archive", PIN, "mod/NutritionRevamp/common/media/lua/shared"],
                              capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            tf.extractall(d, filter="data")
        _PINNED["dir"] = os.path.join(d, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
    return _PINNED["dir"]


@pytest.fixture(scope="module")
def kern():
    return L.Kernel(pinned_shared())


# vanilla's definitions as the server answers them since Task 10c (ruling 13-46's thin pairs removed)
DEFS = {k: dict(v) for k, v in T.DEFS.items()}
for _m in ("weak", "feeble"):
    DEFS[_m]["exclusive"] = [x for x in DEFS[_m]["exclusive"] if x not in ("underweight", "very underweight")]
for _t in ("underweight", "veryunderweight"):
    DEFS[_t]["exclusive"] = [x for x in DEFS[_t]["exclusive"] if x not in ("weak", "feeble")]
VANILLA_LABELS = {"underweight": "Underweight", "veryunderweight": "Very Underweight", "overweight": "Overweight",
                  "obese": "Obese"}


def model(kern):
    D = kern.K.strength.DEFAULTS
    return {"R": float(D.R), "M5": float(D.M5), "Fnm": float(D.Fnm), "b": float(D.b)}


# ---------------------------------------------------------------- the mirrors against the kernel
def test_held_level_is_the_kernels(kern):
    for L_ in (0.2, 3.74, 4.74, 4.76, 4.9, 5.0, 5.3, 5.99, 6.0, 8.8, 9.76, 10.4):
        for Lw in (None, 0, 3, 4, 5, 6, 9, 10):
            want = kern.held(L_, Lw if Lw is not None else float("nan"))
            got = L.held_level(L_, Lw)
            assert got[0] == want[0] and abs(got[1] - want[1]) < 1e-12, (L_, Lw, got, want)
    assert L.held_level(4.9, 5) == (5, 0.0) and L.shown(4.9)[0] == 4     # the drop margin holds 5
    assert L.held_level(4.7, 5)[0] == 4 and L.held_level(6.2, 5)[0] == 6


def test_pin_xp_is_the_kernels(kern):
    totals = kern.table({i: t for i, t in enumerate(L.TOTALS)})
    for n in range(0, 11):
        for frac in (0.0, 0.3, 0.999999):
            assert abs(L.pin_xp(n, frac) - float(kern.K.strength.pinXp(n, frac, totals))) < 1e-9, (n, frac)


def test_energy_rung_is_the_views(kern):
    at = kern.energy_at()
    for es in (0.9, 1.1, 1.249, 1.25, 1.4948, 1.55, 1.6517, 2.0):
        assert L.energy_rung(es, at) == int(kern.K.view.rung(es, kern.K.view.ENERGY_AT)), es


def test_the_staged_names():
    want = L.staged_names(os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "Translate",
                                       "EN", "UI.json"))
    assert want == {"underweight": "Overly Lean", "veryunderweight": "Gaunt", "overweight": "Overfat"}


# ---------------------------------------------------------------- the creation expectations
@pytest.mark.parametrize("kept, native, band, weight, bf, dep, lv", [
    ([], 5, None, None, 0.20, 0.0, 0),
    (["strong", "obese"], 9, "strong", "obese", 0.368, 0.0, 0),
    (["weak", "overweight"], 1, "weak", "overweight", 0.294, 0.0, 0),
    (["underweight"], 5, None, "underweight", 0.10, 0.5556, 3),
    (["weak", "veryunderweight"], 1, "weak", "veryunderweight", 0.065, 0.7219, 4),
    (["feeble", "underweight"], 3, "feeble", "underweight", 0.10, 0.5556, 3)])
def test_expect_body_is_the_task_10b_and_10c_table(kern, kept, native, band, weight, bf, dep, lv):
    e = L.expect_body(kern, kept, 0)
    assert e["native"] == native and e["strengthBand"] == band and e["weight"] == weight
    assert abs(e["bf"] - bf) < 1e-3 and abs(e["fatDep"] - dep) < 1e-4 and e["energyLevel"] == lv
    assert e["frac"] < 1e-9                                         # a creation level is whole (the re-pin's caveat)
    muscle = next((x for x in kept if x in L.MUSCLE), None)
    e0 = L.expect_body(kern, [muscle] if muscle else [], 0)
    assert abs(e["lm"] - e0["lm"]) < 1e-12                          # a weight pick never moves the lean (Task 10c)
    if dep > 0:
        assert abs(e["fmRef"] - e0["fm"]) < 1e-12 and e["es"] > 1.0  # fmRef the no-pick fat; underfed from the start


def test_expected_strips_without_the_anti_stacking_pairs():
    for lab, want in (("a", []), ("b", []), ("c", []), ("d", []), ("e", []), ("f", []),
                      ("g", ["obese", "thickskinned"])):
        s, k = L.expect_strips(dict(L.CASES)[lab], DEFS, 8, 0, 1)
        assert s == want, lab
    # the frozen x43 lib carries ruling 13-46's table of its own and strips Weak on vanilla's definitions; this lib
    # reads the server's definitions only
    assert T.L.expect_strips(("Weak", "Underweight"), DEFS, 8, 0, 1)[0] == ["weak"]
    assert L.expect_strips(("Weak", "Underweight"), DEFS, 8, 0, 1)[0] == []


# ---------------------------------------------------------------- the grades
def test_grade_E():
    ok = {"closed": True, "post": {"eb7.7": 255.0}, "placed": {"inDay_set": True, "before_close": True}}
    assert L.grade_E(ok)[0] == "as_predicted"
    assert L.grade_E(dict(ok, post={"eb7.7": 230.0}))[0] == "falsified"
    assert L.grade_E(dict(ok, post={"eb7.7": -1663.0}))[0] == "falsified"
    assert L.grade_E(dict(ok, placed={"inDay_set": True, "before_close": False}))[0] == "unmeasured"
    assert L.grade_E(dict(ok, closed=False))[0] == "unmeasured"


def test_grade_held_level(kern):
    M = model(kern)
    F = T.L.f_of_level(4.9, 1.0, 1.0, M)
    c = {"closed": True, "pre": {"wroteL": 5}, "post": {"lm": F, "N0": 1.0, "T": 1.0}, "xp": {"level": 5},
         "stats": {"traitList": {}}}
    assert L.grade_held_level(c, M)[0] == "as_predicted"                   # held at 5 inside the drop margin
    assert L.grade_held_level(dict(c, xp={"level": 4}), M)[0] == "falsified"  # shown's floor alone is wrong
    assert L.grade_held_level(dict(c, stats={"traitList": ["feeble"]}), M)[0] == "falsified"
    assert L.grade_held_level(dict(c, stats=None), M)[0] == "unmeasured"


def test_grade_surplus():
    v = {"35_E1": "as_predicted", "35_close1": "as_predicted", "35_E2": "as_predicted", "35_close2": "as_predicted",
         "35_E3": "as_predicted", "35_close3": "as_predicted"}
    assert L.grade_surplus(v, [1, 2, 3])[0] == "as_predicted"
    assert L.grade_surplus(dict(v, **{"35_close3": "falsified"}), [1, 2, 3])[0] == "falsified"
    assert L.grade_surplus(dict(v, **{"35_close3": "unmeasured"}), [1, 2, 3])[0] == "unmeasured"
    v0 = dict(v, **{"35_E0": "as_predicted", "35_close0": "as_predicted", "35_close3": "unmeasured"})
    assert L.grade_surplus(v0, [0, 1, 2, 3])[0] == "unmeasured"            # the lead-in close does not count


def surplus_case(kern, E=258.0, drift=0.0):
    P = kern.params({"StrengthTimeScale": 30.0, "StrengthIncidentalWeight": 1.0})
    pre = T.pre_body(kern)
    pre["eeDay"] = 1900.0
    pre["sig7.7"] = 20 / 7 * 360.0
    S = 2.0 * 20 / 7
    post = T.make_post(kern, P, pre, S, 2.0, E, 1900.0, drift)
    c = {"closed": True, "pre": pre, "post": post}
    c["replay"], c["inputs"] = L.replay_close(kern, P, pre, post)
    return c


def test_grade_surplus_close(kern):
    c = surplus_case(kern)
    v, o = L.grade_surplus_close(c)
    assert v == "as_predicted", o
    assert o["path"]["partition"] == "surplus" and o["path"]["grow"] > 0 and o["path"]["saturated"]
    assert L.grade_surplus_close(surplus_case(kern, drift=2e-6))[0] == "falsified"
    assert L.grade_surplus_close(surplus_case(kern, E=-300.0))[0] == "unmeasured"   # the deficit arm, not the target
    assert L.grade_surplus_close({"closed": False})[0] == "unmeasured"


def case(kern, kept=("underweight",), **kw):
    e = L.expect_body(kern, list(kept), 0)
    body = {k: e[k] for k in ("lm", "fm", "F0", "Fc", "Pk", "N0", "fmRef", "fatT", "thinT", "band")}
    body.update({"lx": 0.0, "levelDue": False, "wroteL": e["native"], "energyState": e["es"] + 0.001})
    traits = [t for t in (e["strengthBand"], e["weight"]) if t]
    pair = {"server_stats": {"weight": e["mass"], "traitList": list(traits)},
            "client_stats": {"weight": e["mass"], "traitList": list(traits)},
            "server_xp": {"level": e["native"], "xp": L.pin_xp(e["native"], e["frac"])},
            "client_xp": {"level": e["native"], "xp": L.pin_xp(e["native"], e["frac"])}, "gap_s": 0.3}
    c = {"landed": True, "expect": e, "body": body, "pair": pair, "want_stripped": [], "levelWrites0": 4,
         "levelWrites1": 6, "mirror": {"body_energyLevel": e["energyLevel"], "body_energyState": e["es"]}}
    c.update(kw)
    return c


def test_grade_case_body(kern):
    assert L.grade_case_body(case(kern))[0] == "as_predicted"
    for key, d in (("fm", 1e-6), ("fmRef", 0.01), ("lm", 1e-6)):
        c = case(kern)
        c["body"][key] += d
        assert L.grade_case_body(c)[0] == "falsified", key
    c = case(kern)
    c["body"]["fmRef"] = c["body"]["fm"]                         # x433's model: no underfed start
    assert L.grade_case_body(c)[0] == "falsified"
    assert L.grade_case_body(case(kern, landed=False))[0] == "unmeasured"


def test_grade_case_traits(kern):
    assert L.grade_case_traits(case(kern))[0] == "as_predicted"
    assert L.grade_case_traits(case(kern, kept=("weak", "veryunderweight")))[0] == "as_predicted"
    c = case(kern)
    c["body"]["thinT"] = 0
    assert L.grade_case_traits(c)[0] == "falsified"
    c = case(kern, kept=("weak", "veryunderweight"))
    c["pair"]["client_stats"]["traitList"] = ["weak", "underweight"]
    assert L.grade_case_traits(c)[0] == "falsified"
    c = case(kern, kept=("strong", "obese"))
    c["pair"]["server_stats"]["traitList"] = ["strong", "overweight"]
    assert L.grade_case_traits(c)[0] == "falsified"
    c = case(kern, want_stripped=["obese"])
    c["pair"]["server_stats"]["traitList"] = c["pair"]["server_stats"]["traitList"] + ["obese"]
    assert L.grade_case_traits(c)[0] == "falsified"
    c = case(kern)
    c["pair"]["gap_s"] = 2.0
    assert L.grade_case_traits(c)[0] == "unmeasured"


def test_grade_case_xp(kern):
    assert L.grade_case_xp(case(kern))[0] == "as_predicted"
    c = case(kern)
    c["body"]["levelDue"] = True
    assert L.grade_case_xp(c)[0] == "falsified"
    assert L.grade_case_xp(case(kern, levelWrites1=5))[0] == "falsified"
    c = case(kern, kept=("feeble", "underweight"))
    c["pair"]["server_xp"]["xp"] = 10500.0 + 2000.0
    assert L.grade_case_xp(c)[0] == "falsified"
    assert L.grade_case_xp(case(kern, levelWrites0=None))[0] == "unmeasured"


def test_grade_case_hunger(kern):
    at = kern.energy_at()
    assert L.grade_case_hunger(case(kern), at)[0] == "as_predicted"
    assert L.grade_case_hunger(case(kern, kept=()), at)[0] == "as_predicted"
    c = case(kern)
    c["body"]["energyState"] = 1.0                               # no fat term at a thin start
    assert L.grade_case_hunger(c, at)[0] == "falsified"
    c = case(kern, kept=("weak", "veryunderweight"))
    c["body"]["energyState"] = 1.524404                          # Task 10c's gain, not fix 2's
    assert L.grade_case_hunger(c, at)[0] == "falsified"
    c = case(kern)
    c["mirror"] = {"body_energyLevel": 2}
    assert L.grade_case_hunger(c, at)[0] == "falsified"
    c = case(kern)
    c["mirror"] = {}
    assert L.grade_case_hunger(c, at)[0] == "as_predicted"       # the client unread does not fail the server's read
    c["body"]["energyState"] = None
    assert L.grade_case_hunger(c, at)[0] == "unmeasured"


def test_grade_names_and_refeed():
    want = {"underweight": "Overly Lean", "veryunderweight": "Gaunt", "overweight": "Overfat"}
    ok = dict(want, obese="Obese")
    assert L.grade_names(ok, want)[0] == "as_predicted"
    assert L.grade_names(VANILLA_LABELS, want)[0] == "falsified"
    assert L.grade_names({k: None for k in ok}, want)[0] == "unmeasured"
    r = {"closed": True, "refeedRisk": 2, "pe": 4, "bmi": 15.5}
    assert L.grade_refeed(r)[0] == "as_predicted"
    assert L.grade_refeed(dict(r, refeedRisk=1))[0] == "falsified"
    assert L.grade_refeed(dict(r, pe=3))[0] == "falsified"
    assert L.grade_refeed(dict(r, closed=False))[0] == "unmeasured"


def test_keep_server_log_never_copies_onto_itself(tmp_path):
    log = tmp_path / "server-stdout.log"
    log.write_text("x")
    copied = []
    L.keep_server_log(str(log), str(tmp_path), copied)
    assert copied == ["server-stdout.log"] and log.read_text() == "x"
    other = tmp_path / "elsewhere.log"
    other.write_text("y")
    L.keep_server_log(str(other), str(tmp_path), copied)
    assert log.read_text() == "y"


# ---------------------------------------------------------------- the pre-boot checks
def test_harness_markers_are_in_the_repository():
    found, ok = L.harness_markers_ok()
    assert ok, found


def test_profiles_and_drivers():
    from pzt import profile
    for name, fixture, users in (("x43c-surplus", "default", ["admin"]), ("x43c-creation", "two", ["admin", "bob"])):
        with open(os.path.join(REPO, "testing", "profiles", name + ".toml"), encoding="utf-8") as fh:
            text = fh.read()
        assert 'path = "' + L.STAGE_MOD + '"' in text and f'fixture = "{fixture}"' in text, name
        assert "Nutrition = false" in text and "DayLength = 1" in text and '"value": "1.0.0"' in text, name
        assert list(profile.load(name).users) == users, name
    with open(os.path.join(REPO, "testing", "profiles", "x43c-surplus.toml"), encoding="utf-8") as fh:
        t = fh.read()
    assert "StrengthTimeScale = 30" in t and "StrengthIncidentalWeight = 1" in t
    for drv, prefix, prof, task in (("x435_surplus.py", "x435", "x43c-surplus", "35"),
                                    ("x436_creation.py", "x436", "x43c-creation", "36")):
        with open(os.path.join(REPO, "testing", "experiments", drv), encoding="utf-8") as fh:
            text = fh.read()
        assert f'PREFIX = "{prefix}"' in text and f'PROFILE = "{prof}"' in text and f'TASK = "{task}"' in text
        assert "import x43c_strength_lib as L" in text


# ---------------------------------------------------------------- the fake world
class World:
    """A minimal server for both sessions: the clock, one record, the minute (eeDay, ebDay = inDay - eeDay, the
    energy state, the level write through heldLevel), the day close through the real kernel (strength day, the
    refeeding day and the PE grade), the creation handler through K.body.create and K.body.new, the death check, the
    stat setter and the trait labels. Flags break one thing each."""

    def __init__(self, kern, flags=None, user="admin", hour=8.0, growth=True):
        self.k = kern
        self.f = flags or {}
        self.user = user
        self.now = 1000.0
        self.age = 24.0 * 10 + hour
        self.age0 = self.age
        self.mult = 1.0
        self.online = {user}
        self.P = kern.params({"StrengthTimeScale": 30.0, "StrengthIncidentalWeight": 1.0}) if growth \
            else kern.params(None)
        self.body = T.pre_body(kern, ageH=self.age)
        self.body.update({"levelDue": False, "wroteL": 5, "eeDay": 0.0, "inDay": 0.0, "ebDay": 0.0,
                          "energyState": 1.0})
        self.rec = {"acute.refeedRisk": 0, "acute.bmi": 0, "acute.starvedDays": 0, "effects.pe": 1}
        self.level, self.xp = 5, 37500.0
        self.counters = {"levelWrites": 0, "created": 0, "runs": 5, "days": 0}
        self.traits = []
        self.last_min = math.floor(self.age * 60)
        self.logs = []
        self.armed = None
        self.dead = False
        self.prof = "base:unemployed"
        self.sets = 0

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
            if self.f.get("dies") and self.age > self.age0 + 30.0:
                self.dead = True
            if self.user in self.online and not (self.dead and self.user == "admin"):
                self.minute()

    def fat_dep(self):
        b = self.body
        return max(0.0, min(1.0, (b["fmRef"] - b["fm"]) / b["fmRef"])) if b["fmRef"] > 0 else 0.0

    def minute(self):
        b = self.body
        b["eeDay"] = b.get("eeDay", 0.0) + 1.4
        b["ebDay"] = b.get("inDay", 0.0) - b["eeDay"]
        es = self.k.state(0.0, self.fat_dep()) + 0.0005
        b["energyState"] = 1.0 if self.f.get("es_flat") else es
        if math.floor(self.age / 24.0) > b["wday"]:
            b["wday"] = math.floor(self.age / 24.0)
            self.close()
        b["lastAgeH"] = self.age
        if b.get("levelDue") and not self.f.get("no_repin"):
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
        b["inDayClosed"] = b["inDay"]
        for key, v in (("eb7", b["ebDay"]), ("p7", b["pDay"]), ("mass7", b["fm"] + b["lm"] + b["lx"])):
            ring = [b[f"{key}.{i}"] for i in range(2, 8)] + [v]
            for i in range(1, 8):
                b[f"{key}.{i}"] = ring[i - 1]
        a = self.k.K.acute.new(self.age)
        self.k.K.acute.refeedDay(a, b["inDayClosed"] / w, w, self.age, False, False, False)
        self.rec.update({"acute.refeedRisk": int(a.refeedRisk) - (1 if self.f.get("refeed_low") else 0),
                         "acute.bmi": float(a.bmi), "acute.starvedDays": int(a.starvedDays),
                         "effects.pe": int(self.k.K.effects.peGrade(a.bmi, a.starvedDays, None))})
        for k in ("eeDay", "ebDay", "pDay", "inDay", "alcDay"):
            b[k] = 0.0
        b["dayIndex"] += 1
        self.counters["days"] += 1
        b["levelDue"] = True

    def write(self):
        b = self.body
        lv = L.level_of(b["lm"], b["N0"], b["T"], self.model())
        n, frac = self.k.held(lv, b["wroteL"] if b.get("wroteL") is not None else float("nan"))
        self.level = n - (1 if self.f.get("level_off") else 0)
        self.xp = L.pin_xp(n, frac)
        band = L.band_of(n)
        self.traits = [t for t in self.traits if t not in L.MUSCLE] + ([band] if band else [])
        if self.f.get("no_band"):
            self.traits = [t for t in self.traits if t not in L.MUSCLE]
        b["wroteL"] = n
        b["levelDue"] = False
        self.counters["levelWrites"] += 1

    def G(self, path):
        P = self.P
        es = self.body.get("energyState")
        tab = {f"{L.STR_STATS}.levelWrites": self.counters["levelWrites"],
               f"{L.NR}.server.minute.stats.runs": self.counters["runs"],
               f"{L.NR}.server.creation.stats.created": self.counters["created"],
               "SandboxVars.CharacterFreePoints": 0, "SandboxVars.NegativeTraitsPenalty": 1,
               "SandboxVars.Nutrition": False, "SandboxVars.DayLength": 1,
               f"{L.NR}.client.received": int(self.now), "TK.picksFired.count": 1,
               f"{L.NR}.client.mirror.body_energyState": es,
               f"{L.NR}.client.mirror.body_energyLevel": L.energy_rung(es, self.k.energy_at())}
        for k in ("R", "M5", "Fnm", "b", "incidental", "xpPerSet", "ts", "k"):
            tab[f"{L.OPT_STR}.{k}"] = float(P[k])
        return tab.get(path)

    def lread(self, args, side):
        parts = args.split()
        root, paths = parts[0], parts[1:]
        out = {"ok": True, "side": side, "root": root, "n": len(paths), "values": {}, "tables": {}, "types": {},
               "missing": {}}
        for p in paths:
            if root.startswith("record:"):
                v = self.body.get(p[5:]) if p.startswith("body.") else self.rec.get(p)
            else:
                v = self.G(p)
            if v is None:
                out["missing"][p] = "nil"
            else:
                out["values"][p] = v
        return out

    def stats(self, side):
        mass = self.body["fm"] + self.body["lm"] + self.body["lx"]
        return {"weight": mass, "traitList": list(self.traits) if self.traits else {}, "worldAge": self.age,
                "wall": self.now}

    def ask(self, node, cmd, args="", timeout=30):
        self.sleep(0.05)
        a = args.split()
        side = "server" if node == "server" else "client"
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
        if cmd == "lua.call":
            return {"ok": True, "side": side, "path": a[0], "nargs": len(a) - 1, "r1": True}
        if cmd == "record.set":
            key = a[1][5:]
            raw = a[2]
            v = True if raw == "true" else False if raw == "false" else float(raw)
            before = self.body.get(key)
            if not (key == "inDay" and self.f.get("inday_ignored")):
                self.body[key] = v + (60.0 if key == "inDay" and self.f.get("e_high") else 0.0)
            return {"ok": True, "side": side, "user": a[0], "path": a[1], "key": key, "before": before, "after": v}
        if cmd == "perk.xp":
            return {"perk": "Strength", "user": self.user, "side": side, "xp": self.xp, "level": self.level}
        if cmd == "xp.grant":
            amt = float(a[2])
            x0 = self.xp
            if self.xp < L.CAP_XP:
                self.xp += amt
                self.body["sigDay"] += amt * float(self.P.incidental)
            return {"ok": True, "perk": "Strength", "amount": amt, "side": side, "xpBefore": x0, "xpAfter": self.xp,
                    "levelBefore": self.level, "levelAfter": self.level}
        if cmd == "stats.set":
            self.sets += 1
            return {"hunger": 0.0, "thirst": 0.0, "applied": {"thirst": "stats", "hunger": "stats"}}
        if cmd == "stats.get":
            return self.stats(side)
        if cmd == "witness.chain":
            ch = a[-1]
            if ch == "isDead":
                return {"ok": True, "value": "true" if self.dead else "false"}
            if ch == "getBodyDamage.getOverallBodyHealth":
                return {"ok": True, "value": "0" if self.dead else "100"}
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
            n = L.norm(a[0])
            d = DEFS.get(n)
            out = {"ok": True, "side": side, "trait": a[0], "cost": d["cost"], "exclusive": d["exclusive"],
                   "free": False, "label": VANILLA_LABELS.get(n, a[0])}
            if side == "client" and not self.f.get("old_names"):
                out["label"] = {"underweight": "Overly Lean", "veryunderweight": "Gaunt",
                                "overweight": "Overfat"}.get(n, out["label"])
            return out
        return {"error": f"fake: unknown {cmd}"}

    def create(self):
        picks = self.armed or []
        self.armed = None
        self.dead = False
        stripped, kept = L.expect_strips(picks, DEFS, 8, 0, 1)
        if self.f.get("list_order"):
            stripped = list(reversed(stripped))
        muscle = next((x for x in kept if x in L.MUSCLE), None)
        pick = next((x for x in kept if x in L.KERNEL_WEIGHT), None)
        spec = self.k.create(muscle.upper() if muscle else None, L.KERNEL_WEIGHT.get(pick), 1, 0)
        if self.f.get("fm_off"):
            spec["fm"] *= 1.01
        nb = T.flat(self.k.K.body.new(self.k.table(spec), 1, self.age))
        nb = {k: v for k, v in nb.items() if not k.startswith("trail")}
        if self.f.get("rung_lost"):
            nb["thinT"] = 0
        self.body = nb
        self.rec = {"acute.refeedRisk": 0, "acute.bmi": 0, "acute.starvedDays": 0, "effects.pe": 1}
        self.body["wroteL"] = None
        self.write()                                   # the creation write
        self.body["levelDue"] = True                   # the first minute re-pins (Task 10c)
        wt = L.weight_word(nb["fatT"], nb["thinT"])
        self.traits = [t for t in self.traits if t in L.MUSCLE] + ([wt] if wt else [])
        if self.f.get("keep_strip") and stripped:
            self.traits.append(stripped[0])
        for s in stripped:
            self.logs.append(f"[NutritionRevamp] creation: {self.user} loses {s} (why)")
        self.logs.append(f"[NutritionRevamp] creation: {self.user} muscle={muscle} weight={pick} prof=0")
        self.counters["created"] += 1


def run_session(kern, task, flags=None, hour=8.0):
    user = "admin" if task == "35" else "bob"
    w = World(kern, flags, user=user, hour=hour, growth=(task == "35"))
    out = T.fresh_out()
    clients = {user: T.FakeClient(user)}
    if user != "admin":
        clients["admin"] = T.FakeClient("admin")
    xs = X.Xs(out, node=lambda side: side, clients=clients, ask=w.ask, budget_s=1e9, clock=w.clock, sleep=w.sleep)
    S = L.Sess(xs, user=user, cli="client" if user == "admin" else "client:bob", game_dir=GAME_DIR, shared_dir=pinned_shared())
    S.run_dir = "."
    body = {"35": S.t35_body, "36": S.t36_body}[task]
    S.body_run(body())
    if task == "35":
        S.t35_grade(kern=kern)
    else:
        if not os.path.isdir(GAME_DIR):
            S.D["S"]["prof_table"] = {"unemployed": (8, 0)}
        S.t36_grade(w.logs, kern=kern)
    assert not out["phase_errors"], out["phase_errors"]
    return {k: v["verdict"] for k, v in out["verdicts"].items()}, out, w


def test_t35_flow(kern):
    v, o, w = run_session(kern, "35", {}, hour=6.0)
    assert set(v.values()) == {"as_predicted"}, (v, {k: o["verdicts"][k]["observed"].get("why") for k in v})
    assert all(f"35_close{k}" in v for k in (1, 2, 3, 4)) and "35_close0" not in v
    E = [o["verdicts"][f"35_E{k}"]["observed"]["E"] for k in (1, 2, 3, 4)]
    assert all(abs(e - L.E_KCAL) <= L.E_TOL for e in E), E
    assert o["checks"]["day4"]["post"]["lm"] > o["checks"]["day1"]["pre"]["lm"]
    assert w.sets >= 4 * 2 and o["verdicts"]["35_close1"]["observed"]["path"]["arm"] in ("growth", "regain")


def test_t35_lead_in(kern):
    # the lead-in day carries no grants, so its close reads no signal: the growth arm reads 0 and the close is
    # unmeasured as the surplus target, while E is still placed and graded
    v, o, _w = run_session(kern, "35", {}, hour=15.0)
    assert v["35_E0"] == "as_predicted" and v["35_close0"] == "unmeasured" and v["35_surplus"] == "as_predicted"
    assert "growth arm read 0" in o["verdicts"]["35_close0"]["observed"]["why"]


@pytest.mark.parametrize("flag, name, verdict", [("drift", "35_close1", "falsified"),
                                                 ("level_off", "35_level1", "falsified"),
                                                 ("inday_ignored", "35_E1", "falsified"),
                                                 ("inday_ignored", "35_surplus", "falsified"),
                                                 ("e_high", "35_E1", "falsified"),
                                                 ("dies", "35_surplus", "unmeasured")])
def test_t35_defects(kern, flag, name, verdict):
    v, _o, _w = run_session(kern, "35", {flag: True}, hour=6.0)
    assert v[name] == verdict, v


def test_t35_inday_ignored_is_x434s_deficit_path(kern):
    v, o, _w = run_session(kern, "35", {"inday_ignored": True}, hour=6.0)
    assert v["35_close1"] == "unmeasured" and o["verdicts"]["35_E1"]["observed"]["E"] < 0


def test_t36_flow(kern):
    v, o, _w = run_session(kern, "36", {})
    assert set(v.values()) == {"as_predicted"}, (v, {k: o["verdicts"][k]["observed"].get("why") for k in v})
    assert o["checks"]["Cg"]["want_stripped"] == ["obese", "thickskinned"]
    assert o["checks"]["E1"]["refeedRisk"] == 2 and o["checks"]["E1"]["pe"] == 4
    assert [p for p, _f in L.Sess(X.Xs(T.fresh_out(), node=str), user="bob").t36_body()][:7] == \
        ["S", "Ca", "Cb", "Cc", "Cd", "Ce", "E1"]


@pytest.mark.parametrize("flag, name", [("fm_off", "36_b_body"), ("rung_lost", "36_d_traits"),
                                        ("no_repin", "36_a_xp"), ("list_order", "36_g_strips"),
                                        ("keep_strip", "36_g_traits"), ("es_flat", "36_e_hunger"),
                                        ("old_names", "36_names"), ("refeed_low", "36_e_refeed")])
def test_t36_defects(kern, flag, name):
    v, _o, _w = run_session(kern, "36", {flag: True})
    assert v[name] == "falsified", v
