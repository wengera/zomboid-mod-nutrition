"""Tests for tools/mod_guide_series.py (Plan 14 Task 4): every series in docs/mod-guide/data.json is non-empty, its
provenance resolves, and one of its values is re-derived here independently, from a direct read of the artifact or
the dataset, a direct kernel call or a short replay on the lupa host (tools/replay_live.py's own entry points), or the
vanilla model's formula functions, never through the series module's own builders. Beside them: the admission test,
the reverse-coverage gate on the real tree, the trait ids (M-10), the burpee bill (M-5), the guide foods' landed
vector (#3182's check) and a mutation case (a kernel constant changed on a scratch copy moves the data and fails
--check).

The full build is the gate `python tools/mod_guide_data.py --check` (about a minute on a process pool); these tests
read the committed data file and never rebuild it whole.
"""
import json
import math
import os
import re
import shutil
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import mod_guide_data as D  # noqa: E402
import mod_guide_series as S  # noqa: E402
import replay_live as RL  # noqa: E402
import vanilla_model as VM  # noqa: E402

ART = os.path.join(REPO, "testing", "artifacts")

with open(os.path.join(REPO, *D.OUT_REL.split("/")), encoding="utf-8") as _fh:
    DATA = json.load(_fh)
SER = {s["id"]: s for s in DATA["series"]}


def pt(sid, x):
    """The y of series sid at x (exact match on a category, nearest on a number)."""
    pts = SER[sid]["points"]
    if isinstance(x, str):
        return next(p[1] for p in pts if p[0] == x)
    return min(pts, key=lambda p: abs(p[0] - x))[1]


def art(run_key, file, *steps):
    with open(os.path.join(ART, S.RUN[run_key], file), encoding="utf-8") as fh:
        node = json.load(fh)
    for s in steps:
        node = node[s]
    return node


def science_value(sid):
    with open(os.path.join(REPO, "docs", "reference", "science.tsv"), encoding="utf-8") as fh:
        for line in fh:
            cells = line.rstrip("\n").split("\t")
            if cells[0] == sid:
                return cells[3]
    raise KeyError(sid)


def arm(events, minutes, paths=(), **kw):
    """A fresh-record replay on the synthetic clock through replay_live.replay_arm (the display defaults)."""
    kw.setdefault("hour_offset", 7.0)
    kw.setdefault("sleep_allowed", False)
    rows, be = RL.replay_arm(events, minutes=minutes, backend="server", rng="half", paths=paths, **kw)
    return rows, be


def eat(minute, pz):
    """A whole eat of pz, its macros read here off the item pass script by regex (float32, as the getters)."""
    with open(os.path.join(REPO, *S.ITEM_PASS.split("/")), encoding="utf-8") as fh:
        text = fh.read()
    block = re.search(r"\bitem %s\s*\{(.*?)\}" % re.escape(pz.split(".")[1]), text, re.S).group(1)
    mac = [RL.float32(float(re.search(r"%s\s*=\s*([-\d.]+)" % k, block).group(1)))
           for k in ("Calories", "Carbohydrates", "Lipids", "Proteins")]
    with open(os.path.join(REPO, "data", "food-nutrients.json"), encoding="utf-8") as fh:
        r = next(i for i in json.load(fh)["items"] if i["pz_id"] == pz)
    return {"minute": minute, "kind": "eat", "fullType": pz, "cal": mac[0], "carb": mac[1], "lip": mac[2],
            "pro": mac[3], "hunger": r["vanilla"]["hunger"] / 100.0}


@pytest.fixture(scope="module")
def kh():
    return S.KHost()


# ---- the whole file ---------------------------------------------------------------------------------------------------

def test_the_built_series_and_the_pending_and_dropped_ids_cover_the_map():
    built = set(SER)
    mapped = {i for c in S.MAP_CHARTS.values() for i in c["series"]}
    assert len(mapped) == 147
    assert built | set(S.PENDING_LIVE) | set(S.DROPPED) == mapped
    assert not (built & set(S.PENDING_LIVE)) and not (built & set(S.DROPPED))
    assert not (set(S.PENDING_LIVE) & set(S.DROPPED))
    assert len(built) == 127 and len(S.PENDING_LIVE) == 10 and len(S.DROPPED) == 10
    assert DATA["charts"] == S.CHARTS
    assert D.coverage_gaps(built, DATA["charts"], S.PENDING_LIVE) == ([], [])


def test_pending_ids_are_the_vanilla_live_gaps_but_the_existing_run():
    vl = {i for c in S.MAP_CHARTS.values() for i in c["series"] if "-v-live" in i}
    assert set(S.PENDING_LIVE) == vl - {"S2d-v-live-weight"}


@pytest.mark.parametrize("sid", sorted(SER))
def test_each_series_is_non_empty_and_its_provenance_resolves(sid):
    s = json.loads(json.dumps(SER[sid]))
    assert s["points"], sid
    assert all(p[1] is not None for p in s["points"])
    D.validate_series(s, commit=D.kernel_commit(), charts=S.CHARTS)


@pytest.mark.parametrize("sid", sorted(SER))
def test_each_series_has_a_rederivation(sid):
    assert sid in CHECKS, "no independent re-derivation for %s" % sid


@pytest.mark.parametrize("sid", sorted(SER))
def test_each_series_value_is_rederived(sid, kh):
    CHECKS[sid](kh)


def test_validation_holds_every_admission_pinned():
    adm = [v for v in DATA["validation"] if v.get("kind") == "admission"]
    assert len(adm) == len(S.ADMISSION_EXPECT)
    for v in adm:
        assert set(v) == {"kind", "run", "quantity", "tolerance", "max_miss", "n", "admitted"}
        assert v["admitted"] == all(v["max_miss"][f] <= v["tolerance"][f][1] for f in v["max_miss"])
    by_run = {}
    for k, want in S.ADMISSION_EXPECT.items():
        by_run.setdefault(S.RUN[k.split(":")[0]], []).append(want)
    for run, wants in by_run.items():
        assert sorted(v["admitted"] for v in adm if v["run"] == run) == sorted(wants), run


def test_the_admission_test_reproduces_x361_and_fails_x364():
    rec, _ = S.admission("x361", False, dict(S.DEFAULT_TOL))
    assert rec["admitted"] and rec["max_miss"]["HUNGER"] < 0.002
    stored = next(v for v in DATA["validation"] if v["run"] == S.RUN["x361"])
    assert stored["max_miss"]["HUNGER"] == rec["max_miss"]["HUNGER"]
    rec, _ = S.admission("x364", False, dict(S.DEFAULT_TOL))
    assert not rec["admitted"] and rec["max_miss"]["HUNGER"] > 0.002


def test_the_admission_test_fails_a_run_against_a_tighter_tolerance():
    rec, _ = S.admission("x361", False, {"HUNGER": ("abs", 1e-6)})
    assert not rec["admitted"]


def test_a_flipped_admission_fails_the_build(monkeypatch):
    monkeypatch.setitem(S.ADMISSION_EXPECT, "x37g", False)
    with pytest.raises(D.ProvenanceError, match="re-rule"):
        S.adm("x37g")


def test_the_trait_ids_the_s5b_series_use(kh):
    # M-10: the creation reads the muscle pick off K.strength.MUSCLE_TRAITS and the weight pick off
    # K.traits.WEIGHT_TRAITS, upper-case registry names (not "weak", "overweight")
    muscle = [kh.K.strength.MUSCLE_TRAITS[i] for i in range(1, 5)]
    weight = [kh.K.traits.WEIGHT_TRAITS[i] for i in range(1, 6)]
    assert "WEAK" in muscle and "STRONG" in muscle and "OVERWEIGHT" in weight and "VERY_UNDERWEIGHT" in weight
    for traits, _ in S.S5B.values():
        assert all(t in muscle + weight for t in traits)


def test_the_burpee_set_bills_7_5_met():
    # M-5: the SX2 replay's set minutes bill K.energy.EXERCISE_MET.burpees
    ev = [{"minute": 30, "kind": "activity", "exercising": True},
          {"minute": 30, "kind": "setpath", "path": S.EXE_PATH, "value": "burpees"},
          {"minute": 40, "kind": "activity", "exercising": False}]
    rows, _ = arm(ev, 45, ("body.met",))
    assert {r["body.met"] for r in rows[30:40]} == {7.5}
    assert rows[29]["body.met"] == 1.3


@pytest.mark.parametrize("pz", S.GUIDE_FOODS + ("Base.Orange",))
def test_a_guide_food_lands_its_item_pass_vector(pz):
    # #3182's check offline: the vector the intake chain lands for a whole eat equals the item pass's record
    be = RL.ServerReplay(user="admin", hour_offset=7.0, rng="half", sleep_allowed=False)
    RL.run(be, RL.synthetic_ages(2), [], [], start_age=0.0)
    e = S.eat(0, pz)
    spec = be.rt.table()
    for k in ("fullType", "cal", "carb", "lip", "pro", "foodType"):
        if e.get(k) is not None:
            spec[k] = e[k]
    spec.instBase = e["hunger"]
    spec.frac = 1.0
    v = be.R.eatItem("admin", spec)
    table = be.NR.data.nutrients.get(pz)                                  # the mod's table, the vector #3182 read
    with open(os.path.join(REPO, "data", "food-nutrients.json"), encoding="utf-8") as fh:
        rec = next(i for i in json.load(fh)["items"] if i["pz_id"] == pz)["per_item"]
    for k in ("calories", "carbs", "lipids", "proteins", "vitC", "iron", "sodium", "fibre"):
        assert v[k] == pytest.approx(table[k], rel=1e-6, abs=1e-6), (pz, k)        # float32 macros only
        assert v[k] == pytest.approx(rec[k], rel=1e-4, abs=1e-2), (pz, k)          # the record, to the table's digits


# ---- the mutation case ---------------------------------------------------------------------------------------------

def test_a_kernel_constant_changed_on_a_scratch_copy_moves_the_data_and_fails_check(tmp_path):
    _, server_host, _ = RL._lua()
    lua = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
    scratch = tmp_path / "lua"
    shutil.copytree(lua, scratch)
    charts = {"H3": S.MAP_CHARTS["H3"]}
    out = str(tmp_path / "data.json")
    import io
    from contextlib import redirect_stderr, redirect_stdout
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        assert D.main(["--write"], series_defs=[S.s_h3], charts=charts, validation=[], pending=(), out=out) == 0
        assert D.main(["--check"], series_defs=[S.s_h3], charts=charts, validation=[], pending=(), out=out) == 0
    path = scratch / "shared" / "NR_Kernel_Strength.lua"
    text = path.read_text(encoding="utf-8")
    old = "    k = 0.009906127265972144,"
    assert text.count(old) == 1
    path.write_text(text.replace(old, "    k = 0.0105,"), encoding="utf-8", newline="\n")
    saved = (server_host.SHARED, server_host.SERVER)
    try:
        server_host.SHARED = str(scratch / "shared")
        server_host.SERVER = str(scratch / "server")
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            assert D.main(["--check"], series_defs=[S.s_h3], charts=charts, validation=[], pending=(), out=out) == 1
        assert "out of date" in err.getvalue()
        moved = D.build([S.s_h3], charts=charts, validation=[], pending=())
    finally:
        server_host.SHARED, server_host.SERVER = saved
    lvl = {s["id"]: s["points"][-1][1] for s in moved["series"]}
    assert lvl["H3-m-level"] > pt("H3-m-level", 365)
    assert lvl["H3-v-model-x1"] == pt("H3-v-model-x1", 365.0)          # the vanilla line does not read the kernel


# ======================================================================================================================
# The re-derivations, one a series
# ======================================================================================================================

CHECKS = {}


def check(*ids):
    def deco(fn):
        for i in ids:
            CHECKS[i] = (lambda kh, i=i: fn(kh, i))
        return fn
    return deco


K_IDLE = VM.HUNGER_INCREASE            # dH/dt = k (1 - H), awake idle, StatsDecrease 3


def h_after(h0, seconds):
    return 1 - (1 - h0) * math.exp(-K_IDLE * seconds)


# ---- vanilla-model series: the formulas by hand ---------------------------------------------------------------------

@check("H1-v-model")
def _(kh, sid):
    assert pt(sid, 0.0) == pytest.approx(0.25 - 0.24)                  # 0.01: above the minimum, no timer
    assert pt(sid, 6.0) == pytest.approx(h_after(0.01, 6 * 3600), abs=1e-12)


@check("H2-v-model")
def _(kh, sid):
    # the store from 0: +1500 a day against 0.016 x 86400 = 1382.4 burnt; its peak first passes 1000 on the third day
    assert pt(sid, 1.0) == 80.0 and pt(sid, 2.0) == 80.0 and pt(sid, 3.0) > 80.0


@check("H3-v-model-x1", "S4a-v-model-x1")
def _(kh, sid):
    sets = int(365 * 24 / 8.4) + 1                                       # one every 8.4 h from hour 0
    xp = 37500 + 360 * sets
    assert xp == 412980 and VM.level_for_xp(xp) == 9 == pt(sid, 365.0)


@check("H3-v-model-x15")
def _(kh, sid):
    n = math.ceil((487500 - 37500) / 540.0)                              # sets to level 10 at 540 XP a set
    day = math.ceil((n - 1) * 8.4 / 24.0)
    assert pt(sid, day) == 10 and pt(sid, day - 1) == 9


@check("S4a-v-model-x07")
def _(kh, sid):
    assert pt(sid, 365.0) == VM.level_for_xp(37500 + 252 * (int(365 * 24 / 8.4) + 1))


@check("S4b-v-model")
def _(kh, sid):
    assert pt(sid, 0.0) == 5 and pt(sid, 10.0) == 10


@check("S4c-v-model")
def _(kh, sid):
    # the second year: the first rust step 48.6 days after the last set, then 1 XP a 1200-unit bucket (1.2 a day)
    xp = 412980 - math.floor((365 - 48.6) * 1440 / 1200)
    assert VM.level_for_xp(xp) == 9 == pt(sid, 730.0)


@check("S5b-v-model-level")
def _(kh, sid):
    first = (20000 + 50000) / 1440.0                                     # the rust timer from -50 000 to 20 000
    assert round(first, 1) == 48.6
    assert pt(sid, 48.0) == 5 and pt(sid, 49.0) == 4


@check("SS1-v-model")
def _(kh, sid):
    assert pt(sid, 20.0) == 9 and pt(sid, 0.0) == 4                     # no sets: rust takes 5 to 4 in the year


@check("S1a-v-model")
def _(kh, sid):
    assert pt(sid, 1.0) == 0.0                                            # the tin at 08:00 clamps to 0
    assert pt(sid, 1.0 / 6) == pytest.approx(h_after(0.0, 600), abs=1e-12)


@check("S1b-v-model")
def _(kh, sid):
    assert pt(sid, 36.0) == VM.moodle_level(h_after(0, 36 * 3600), (0.15, 0.25, 0.45, 0.70)) == 4
    assert pt(sid, 34.0) == 3


@check("S1c-v-model")
def _(kh, sid):
    assert pt(sid, 24.0) == pytest.approx(8.0e-6 * 86400)


@check("ST1-v-model")
def _(kh, sid):
    assert pt(sid, 10.0) == pytest.approx(8.0e-6 * 36000)


@check("S2a-v-model")
def _(kh, sid):
    # the 20:00 eat takes HUNGER to 0 and fills 0.24 x 13000 = 3120 units, 1040 game seconds at 3 a second
    assert pt(sid, 30.0) == pytest.approx(h_after(0.0, 30 * 3600 - 1040), abs=1e-9)


@check("S2c-v-model", "S5c-v-model", "S6c-v-model")
def _(kh, sid):
    want = 0.0 if sid == "S2c-v-model" else 1.0
    assert all(p[1] == want for p in SER[sid]["points"])


@check("S2d-v-model-health")
def _(kh, sid):
    t4 = -math.log(1 - 0.70) / K_IDLE / 3600                            # 34.84 h to HUNGRY 4
    per_h = 0.0165 / 50 * 120 * 90                                        # 3.564 a game hour at DayLength 4
    assert pt(sid, 50.0) == pytest.approx(100 - per_h * (50 - t4), abs=0.6)   # within one 10-minute segment


@check("S2d-v-model-weight")
def _(kh, sid):
    per_day = 8.5e-6 * min(1.0, 2200 / 2500) * 86400                   # the loss below the floor store
    assert (pt(sid, 80.0) - pt(sid, 90.0)) / 10 == pytest.approx(per_day, rel=1e-6)


@check("S5a-v-model-weight")
def _(kh, sid):
    assert [p[1] for p in SER[sid]["points"]] == [80.0, 105.0, 95.0, 70.0, 60.0, 70.0]


@check("S5a-v-model-level")
def _(kh, sid):
    assert [p[1] for p in SER[sid]["points"]] == [5, 9, 0, 5, 0, 3]


@check("S6a-v-model")
def _(kh, sid):
    assert all(p[1] == pytest.approx(-10 / 100 * 0.25) for p in SER[sid]["points"])


@check("S6b-v-model")
def _(kh, sid):
    assert pt(sid, 1.0) == pytest.approx(400 * 0.05 * 0.3)


@check("SB2-v-model")
def _(kh, sid):
    assert [p[1] for p in SER[sid]["points"]] == [1, 0, 1]               # 90 and 85 kg Overweight, 80 kg none


@check("SX1-v-model")
def _(kh, sid):
    assert pt(sid, "idle") == pytest.approx(0.016 * 3600) and pt(sid, "running") == pytest.approx(0.13 * 3600)


@check("SX2-v-model")
def _(kh, sid):
    h0 = float(re.search(r"\((\d\.\d+)\)", SER[sid]["note"]).group(1))
    assert pt(sid, 0.0) == pytest.approx(h_after(h0, 1800), abs=1e-4)


# ---- datasets: the files read directly ------------------------------------------------------------------------------

def _food_rec(pz):
    with open(os.path.join(REPO, "data", "food-nutrients.json"), encoding="utf-8") as fh:
        return next(i for i in json.load(fh)["items"] if i["pz_id"] == pz)


@check("H4-m-kcal", "H4-m-carb", "H4-m-fat", "H4-m-pro", "SN1-m-vitC", "SN1-m-fibre", "SN1-m-iron", "SN1-m-sodium")
def _(kh, sid):
    field = {"kcal": "calories", "carb": "carbs", "fat": "lipids", "pro": "proteins", "vitC": "vitC",
             "fibre": "fibre", "iron": "iron", "sodium": "sodium"}[sid.split("-")[-1]]
    assert pt(sid, "Tuna") == _food_rec("Base.TunaTinOpen")["per_item"][field]


@check("H4-v-kcal", "H4-v-carb", "H4-v-fat", "H4-v-pro")
def _(kh, sid):
    field = {"kcal": "Calories", "carb": "Carbohydrates", "fat": "Lipids", "pro": "Proteins"}[sid.split("-")[-1]]
    with open(os.path.join(D.INSTALL, "media", "scripts", "generated", "items", "food.txt"), encoding="utf-8",
              errors="replace") as fh:
        text = fh.read()
    block = re.search(r"\bitem Burger\s*\{(.*?)\n\s*\}", text, re.S).group(1)
    m = re.search(r"^\s*%s\s*=\s*([-\d.]+)" % field, block, re.M)
    want = float(m.group(1)) if m else None
    assert pt(sid, "Burger") == want
    assert pt(sid, "Tuna") == _food_rec("Base.TunaTinOpen")["vanilla"][
        {"Calories": "calories", "Carbohydrates": "carbohydrates", "Lipids": "lipids", "Proteins": "proteins"}[field]]


# ---- live series: the artifact read directly -------------------------------------------------------------------------

@check("S2d-v-live-weight")
def _(kh, sid):
    s = art("scen", "scenario-nutrition_3day_fast.json", "test", "samples")
    assert pt(sid, (s[-1]["worldAge"] - s[0]["worldAge"]) / 24) == s[-1]["weight"] == pytest.approx(78.574, abs=1e-3)


@check("S3b-m-live-U", "S3b-m-live-B")
def _(kh, sid):
    leaf = "server_U" if sid.endswith("U") else "moodLast_b"
    days = art("x34r", "rows.json", "row13", "days", "days")
    assert [p[1] for p in SER[sid]["points"]] == [days[str(d)][leaf] for d in range(5)]
    assert {days[str(d)]["session"] for d in range(5)} == {"x341", "x342"}


@check("S5a-m-live-lean", "S5a-m-live-fat", "S5a-m-live-weight", "S5a-m-live-level")
def _(kh, sid):
    v = art("x436", "creation.json", "verdicts")
    got = {"lean": v["36_b_body"]["observed"]["record"]["lm"], "fat": v["36_b_body"]["observed"]["record"]["fm"],
           "weight": v["36_b_body"]["observed"]["derived"]["mass"],
           "level": v["36_b_xp"]["observed"]["client_level"]}[sid.split("-")[-1]]
    assert pt(sid, "Strong + Obese") == got


@check("S5c-m-live")
def _(kh, sid):
    v = art("x436", "creation.json", "verdicts")
    assert [p[1] for p in SER[sid]["points"]] == [v["36_%s_hunger" % c]["observed"]["es"] for c in "def"]


@check("S6c-m-live", "SC1-m-live-debt")
def _(kh, sid):
    closes = art("x30g", "rows.json", "row11", "closes")
    assert [p[1] for p in SER[sid]["points"]] == [c["debt_after"] for c in closes]


@check("SC1-m-live-booked")
def _(kh, sid):
    n = art("x30g", "rows.json", "row11", "nights")
    assert SER[sid]["points"] == [[x["label"], x["booked_h"]] for x in n]


@check("SE1-m-live-liquid", "SE1-m-live-fill")
def _(kh, sid):
    rows = art("x363", "minute-ring-admin-1.json", "rows_list")
    key = "stomach.liquid" if sid.endswith("liquid") else "stomachFill"
    a0 = rows[0]["age"]
    assert SER[sid]["points"][1] == [(rows[5]["age"] - a0) * 60.0, rows[5][key]]


@check("SH1-m-live")
def _(kh, sid):
    r = art("x36g", "grade.json", "sessions", "x361", "readings", "readings")
    assert SER[sid]["points"] == [[650.0, r["C650_request_vs_anchor"]["live_min"]],
                                  [400.0, r["C400_held_vs_180"]["live_min"]]]


@check("ST2-m-live-na")
def _(kh, sid):
    by = art("x28g", "rows.json", "sodium", "by_day")
    assert [p[1] for p in SER[sid]["points"]] == [by[str(d)]["na_change_per_24h"] for d in range(1, 6)]


@check("SD1-m-live")
def _(kh, sid):
    r = art("x161b", "body.json", "summaries", "I", "health", "per_game_h")
    assert SER[sid]["points"][1][0] == pytest.approx(100 / -r / 24)


@check("SX1-m-live")
def _(kh, sid):
    sets = art("x37g", "grade.json", "sessions", "x371", "sets")
    burpees = [b["billed"] for s in sets for b in s["bills"] if b["type"] == "burpees"]
    assert pt(sid, "burpees") == burpees[0] * 80.0 == 600.0


@check("SV1-m-live")
def _(kh, sid):
    rows = art("x401", "accept.json", "verdicts", "OF", "observed", "rows")
    assert SER[sid]["points"] == [[r["server_mass"], r["levels"]] for r in rows]


# ---- study series: the register's value cell -------------------------------------------------------------------------

@check("S2b-study-1613")
def _(kh, sid):
    a, b = map(float, re.match(r"([\d.]+) vs ([\d.]+) MJ", science_value("S1613")).groups())
    assert pt(sid, "day 2") == a / b


@check("S2b-study-1614")
def _(kh, sid):
    v = science_value("S1614")
    assert "7% greater on day 2" in v and "not different on day 3" in v
    assert SER[sid]["points"] == [["day 2", 1.07], ["day 3", 1.0]]


@check("S2c-study")
def _(kh, sid):
    assert "~100 kcal/day per kg" in science_value("S1254")
    x, y = SER[sid]["points"][-1]
    assert y / x == pytest.approx(95.0 / 0.76)


@check("S3a-study-0224", "S3a-study-0225", "SD2-study")
def _(kh, sid):
    sci = {"S3a-study-0224": "S0224", "S3a-study-0225": "S0225", "SD2-study": "S0225"}[sid]
    days = float(re.search(r"(\d+) days", science_value(sci)).group(1))
    p = SER[sid]["points"][0]
    assert (p[1] if sid == "SD2-study" else p[0]) == days


@check("S3c-study")
def _(kh, sid):
    assert "within one week" in science_value("S0229") and SER[sid]["points"][0][0] == 45 + 7


@check("S4b-study")
def _(kh, sid):
    v = science_value("S1915")
    assert "25.0 kg/m2" in v
    P = kh.K.strength.DEFAULTS
    H = float(kh.K.HEIGHT_M)
    F = (25.0 - 6.3 * (1.80 - H)) * H * H                                # S1915's normalisation undone at the mod's height
    assert pt(sid, 0.0) == pytest.approx(float(kh.K.strength.level(F, 1.0, P.Tmax, P)), rel=1e-12)


@check("S4c-study-0618")
def _(kh, sid):
    v = science_value("S0618")
    assert "−5 to −15 %" in v and "<8 wk" in v
    L365 = pt("S4c-m-kernel", 365)
    assert SER[sid]["points"][2] == [786, L365]


@check("S4c-study-0078")
def _(kh, sid):
    assert "strength remained elevated" in science_value("S0078") and SER[sid]["points"] == [[505, 5.0]]


@check("S6c-study")
def _(kh, sid):
    assert "(22%)" in science_value("S1566") and pt(sid, 2.0) == 1.22


@check("SH1-study-1247")
def _(kh, sid):
    v = science_value("S1247")
    assert [p[1] for p in SER[sid]["points"]] == [float(x) for x in re.findall(r"(\d+) \+/- \d+ min", v)]


@check("SH1-study-1248")
def _(kh, sid):
    lo, hi = map(float, re.match(r"(\d+)-(\d+) min", science_value("S1248")).groups())
    assert [p[1] for p in SER[sid]["points"]] == [lo, hi]


@check("SH2-study")
def _(kh, sid):
    six, three = map(float, re.search(r"hunger AUC (\d+) \+/- \d+ mm.24 h on six meals vs (\d+)",
                                      science_value("S1608")).groups())
    assert pt(sid, "six meals") == six / three


# ---- kernel series: a direct kernel call or a short replay -------------------------------------------------------------

def body_new(kh, muscle=None, weight=None):
    K = kh.K
    return K.body.new(K.body.create(muscle, weight, K.strength.DEFAULTS, 1, 0), 1, 0)


def days_of(kh, sched):
    K = kh.K
    P = K.strength.DEFAULTS
    b = body_new(kh)
    for n, S_, p, E in sched:
        for _ in range(n):
            K.strength.day(b, S_, p, E, 2600.0, 0.0, P, 1.0)
    return b, float(K.strength.level(b.lm, b.N0, b.T, P))


@check("H3-m-level", "S4a-m-perfect", "S4a-m-lowprotein", "S4a-m-deficit", "S4b-m-level", "S4c-m-kernel",
       "SS1-m-kernel")
def _(kh, sid):
    sched = {"S4a-m-lowprotein": (20.0, 0.8, 260.0), "S4a-m-deficit": (20.0, 2.0, -500.0),
             "SS1-m-kernel": (3.0, 1.6, 260.0)}.get(sid, (20.0, 2.0, 260.0))
    n = {"SS1-m-kernel": 365, "S4c-m-kernel": 30}.get(sid, 28)       # a day each series samples
    _, L = days_of(kh, [(n,) + sched])
    x = 3.0 if sid == "SS1-m-kernel" else (28 / 365.0 if sid == "S4b-m-level" else n)
    if sid == "S4b-m-level":
        assert pt(sid, x) == pytest.approx(L, abs=0) and SER[sid]["points"][4][0] == pytest.approx(28 / 365.0)
    else:
        assert pt(sid, x) == L


@check("H3-m-written")
def _(kh, sid):
    K = kh.K
    w = None
    b = body_new(kh)
    P = K.strength.DEFAULTS
    w = K.strength.heldLevel(K.strength.level(b.lm, b.N0, b.T, P), None)[0]
    for _ in range(200):
        K.strength.day(b, 20.0, 2.0, 260.0, 2600.0, 0.0, P, 1.0)
        w = K.strength.heldLevel(K.strength.level(b.lm, b.N0, b.T, P), w)[0]
    assert pt(sid, 200) == w


@check("S4b-m-cap")
def _(kh, sid):
    K = kh.K
    P = K.strength.DEFAULTS
    b = body_new(kh)
    assert pt(sid, 0.0) == float(K.strength.level(b.Fc, b.N0, P.Tmax, P))


@check("SB1-m-def-rest", "SB1-m-def-train", "SB1-m-sur-rest", "SB1-m-sur-train")
def _(kh, sid):
    sched = {"SB1-m-def-rest": (0.0, 1.2, -500.0), "SB1-m-def-train": (12.0, 2.0, -500.0),
             "SB1-m-sur-rest": (0.0, 1.2, 500.0), "SB1-m-sur-train": (12.0, 2.0, 500.0)}[sid]
    b, _ = days_of(kh, [(10,) + sched])
    assert pt(sid, 10) == float(b.lm) + float(b.lx)


@check("SB2-m-kernel")
def _(kh, sid):
    # lean 76.5 kg, fat 13.5: the fat index 13.5 / 2.89 x 52.02 / 76.5 is under the male cut 6 (#3856)
    assert 13.5 / 2.89 * 52.02 / 76.5 < 6 and pt(sid, "lean 90 kg") == 0
    b = kh.table({"lm": 59.5, "fm": 25.5, "fatT": 0, "thinT": 0})
    kh.K.traits.axes(b, 1)
    assert pt(sid, "soft 85 kg") == b.fatT == 1


@check("SX1-m-kernel")
def _(kh, sid):
    assert pt(sid, "burpees") == 7.5 * 80 and pt(sid, "idle") == pytest.approx(1.3 * 80)


@check("SV1-m-kernel")
def _(kh, sid):
    assert pt(sid, 1000) == kh.K.view.fullnessLevel(1000.0)


@check("SD1-m-kernel")
def _(kh, sid):
    d, code = S.scurvy_drain(kh)
    assert code == 2 and d == pytest.approx(1 / 100.8)                  # #3106: 0.00992063 a game minute
    assert pt(sid, 1.0) == pytest.approx(100 - d * 1440)


@check("SD2-m-marginal", "SD2-m-clinical")
def _(kh, sid):
    k = 0.047427999622147034                                              # NR_Data_Records vitC k
    if sid.endswith("marginal"):
        assert pt(sid, "vitC") == math.ceil(math.log(1 / 0.70) / k)
    else:
        assert pt(sid, "vitC") in (40, 41) and abs(math.log(1 / 0.15) / k - 40) < 1e-9


@check("SH1-m-kernel")
def _(kh, sid):
    M = S._kt("test_satiety_meal_studies")
    C = S._kt("conftest")
    assert [p[1] for p in SER[sid]["points"]] == M.callahan(C.LuaHost())


@check("ST2-m-kernel")
def _(kh, sid):
    days, _ = S._kt("test_sodium_balance").simulate(1, 0.0)
    assert pt(sid, 1) == days[0]["na_end"]


@check("H1-m-kernel")
def _(kh, sid):
    rows, _ = arm([], 1440)
    m = int(round(RL.request_minute(rows, 0.0)))
    assert pt(sid, 0.0) == rows[m - 1]["HUNGER"] >= 0.25


@check("H2-m-fat", "H2-m-lean", "H2-m-total")
def _(kh, sid):
    ev = [{"minute": m, "kind": "meal", "size": 500.0, "comp": RL.MIXED} for m in (0, 300, 660)]
    ev += [{"minute": m, "kind": "autodrop", "g": 600.0} for m in (60, 300, 540, 780)]
    rows, _ = arm(sorted(ev, key=lambda e: e["minute"]), 1440, ("body.fm", "body.lm", "body.lx"))
    r = rows[1439]
    want = {"fat": r["body.fm"], "lean": r["body.lm"] + r["body.lx"],
            "total": r["body.fm"] + r["body.lm"] + r["body.lx"]}[sid.split("-")[-1]]
    assert pt(sid, 1.0) == want


@check("S1a-m-kernel")
def _(kh, sid):
    rows, _ = arm([eat(60, "Base.TunaTinOpen")], 120)
    assert pt(sid, 70 / 60.0) == rows[69]["HUNGER"]


@check("S1b-m-kernel")
def _(kh, sid):
    rows, _ = arm([], 36 * 60, (S.SIG,))
    assert pt(sid, 36.0) == int(rows[-1][S.SIG] // 1000) % 10


@check("S1c-m-kernel", "ST1-m-kernel")
def _(kh, sid):
    rows, _ = arm([], 120)
    assert pt(sid, 2.0) == rows[119]["THIRST"]


@check("S2a-m-kernel")
def _(kh, sid):
    O = S._kt("test_replay_live_oracle")
    _, fast, _ = O.fast_plans()
    ev = [{"minute": m, "kind": "meal", "size": k} for m, k in sorted(fast.items()) if m < 3 * 1440 + 8 * 60]
    rows, _ = arm(ev, 3 * 1440 + 8 * 60, hour_offset=0.0)
    assert pt(sid, -12.0) == rows[3 * 1440 + 8 * 60 - 1]["HUNGER"]


@check("S2b-m-kernel")
def _(kh, sid):
    r = S._kt("test_replay_live_energy").fast_server()
    assert [p[1] for p in SER[sid]["points"]] == [r["r2"], r["r3"]]


@check("S2c-m-kernel")
def _(kh, sid):
    E = S._kt("test_replay_live_energy")
    base, _ = E.fat_loss_intake(kh, 0.0)
    y, x = E.fat_loss_intake(kh, 0.25)
    assert pt(sid, x) == y - base


@check("S2d-m-mass")
def _(kh, sid):
    rows, _ = arm([{"minute": m, "kind": "autodrop", "g": 600.0} for m in (60, 300, 540, 780)], 1440,
                  ("body.fm", "body.lm", "body.lx"))
    r = rows[-1]
    assert pt(sid, 1.0) == r["body.fm"] + r["body.lm"] + r["body.lx"]


@check("S3a-m-pool", "S3a-m-grade", "S3c-m-pool")
def _(kh, sid):
    # tuna carries no vitamin C: the pool decays exactly exp(-k t) from the first sight (ZOH), t days of drains
    k = float(kh.NR.data.records.REC.vitC.k)
    d = 44.0 if sid == "S3c-m-pool" else 30.0
    p = math.exp(-k * (d - 1 / 1440.0))
    if sid == "S3a-m-grade":
        assert pt(sid, 30.0) == 3 and pt(sid, 60.0) == 4 and math.exp(-k * 30) < 0.45
    else:
        assert pt(sid, d) == pytest.approx(p, rel=1e-9)


@check("S3b-m-kernel-U")
def _(kh, sid):
    rows, _ = arm([eat(m, "Base.TunaTinOpen") for m in (60, 300, 540, 780)], 1440)
    assert pt(sid, 1.0) == rows[1439]["UNHAPPINESS"]


def _s5b_rows(name, minutes, paths):
    traits, perk = S.S5B[name]
    be = RL.ServerReplay(player={"traits": traits, "female": False}, hour_offset=7.0, rng="half",
                         sleep_allowed=False)
    be.p.st.perk = perk
    return RL.run(be, RL.synthetic_ages(minutes), [], list(paths), start_age=0.0)


@check("S5b-m-strong-level", "S5b-m-weak-level", "S5b-m-none-level")
def _(kh, sid):
    name = sid.split("-")[2]
    want = {"strong": 9, "weak": 1, "none": 5}[name]                     # the mod's start levels (#3855)
    rows = _s5b_rows(name, 2, ("body.wroteL",))
    assert pt(sid, 0.0) == rows[0]["body.wroteL"] == want


@check("S5b-m-gaunt-weight", "S5b-m-overfat-weight", "S5b-m-none-weight", "S5c-m-gaunt", "S5c-m-none")
def _(kh, sid):
    name = {"gaunt": "gaunt", "overfat": "overweight", "none": "none"}[sid.split("-")[2]]
    rows = _s5b_rows(name, 2, ("body.fm", "body.lm", "body.lx", "body.energyState"))
    r = rows[0]
    if sid.startswith("S5c"):
        assert pt(sid, 0.0) == r["body.energyState"]
    else:
        assert pt(sid, 0.0) == r["body.fm"] + r["body.lm"] + r["body.lx"]


@check("S6a-m-day1", "S6a-m-day14")
def _(kh, sid):
    if sid.endswith("day1"):
        ev = [{"minute": m, "kind": "drink", "fluid": "Coffee", "litres": 0.25} for m in (60, 300, 540)]
        rows, _ = arm(ev, 1440, ("acute.caf",))
        assert pt(sid, 10.0) == rows[599]["acute.caf"]
    else:
        # between cups the caffeine decays on the 5.0 h half-life (K.acute.CAF_THALF_H): 23:00 to 07:00 of day 14
        a, b = pt(sid, 16.0), pt(sid, 24.0)
        assert b == pytest.approx(a * 0.5 ** (8.0 / float(kh.K.acute.CAF_THALF_H)), rel=1e-3)   # the gut's tail


@check("S6b-m-bac", "S6b-m-intox", "S6b-m-hangover")
def _(kh, sid):
    ev = [{"minute": m, "kind": "drink", "fluid": "Beer", "litres": 0.3} for m in (60, 80, 100, 120)]
    rows, _ = arm(ev, 1440, ("acute.bac", "effects.intoxTarget", "acute.hang"))
    path = {"bac": "acute.bac", "intox": "effects.intoxTarget", "hangover": "acute.hang"}[sid.split("-")[-1]]
    assert pt(sid, 190 / 60.0) == rows[189][path]


@check("S6c-m-kernel")
def _(kh, sid):
    ev = [{"minute": 16 * 60, "kind": "sleep", "asleep": True}, {"minute": 1440, "kind": "sleep", "asleep": False},
          {"minute": 1440 + 20 * 60, "kind": "sleep", "asleep": True},
          {"minute": 2880, "kind": "sleep", "asleep": False}]
    ev += [{"minute": d * 1440 + m, "kind": "meal", "size": "request", "comp": RL.MIXED} for d in range(2)
           for m in (60, 360, 780)]
    ev += [{"minute": d * 1440 + m, "kind": "autodrop", "g": 600.0} for d in range(2) for m in (60, 300, 540, 780)]
    rows, _ = arm(sorted(ev, key=lambda e: e["minute"]), 2 * 1440 + 60, ("acute.debtH",), sleep_allowed=True)
    debt = rows[2 * 1440 + 59]["acute.debtH"]
    assert debt > 0
    assert pt(sid, (2 * 1440 + 60) / 1440.0) == float(kh.K.satiety.sleepFactor(debt))


@check("SE1-m-kernel-fill")
def _(kh, sid):
    rec, kept = S.admission("x363", False, {"stomachFill": ("abs", 0.002)}, keep=("stomachFill",))
    a0 = art("x363", "minute-ring-admin-1.json", "rows_list")[0]["age"]
    s = sorted(kept, key=float)[10]
    assert pt(sid, (kept[s][0] - a0) * 60.0) == kept[s][1]


@check("SH2-m-kernel")
def _(kh, sid):
    assert pt(sid, "six meals") == pytest.approx(0.9852, abs=1e-4)      # re-run in full below (slow)
    r = S.j_sh2()
    assert pt(sid, "six meals") == r["six"] / r["three"]


@check("SM1-m-kernel")
def _(kh, sid):
    eps = float(kh.K.hybrid.FLOOR_EPS)
    _, kept = S.admission("x343", False, S.mood_tol(eps), keep=("UNHAPPINESS",))
    a0 = art("x34r", "rows.json", "row13", "release", "from_age")
    first = SER[sid]["points"][0]
    s = next(s for s in sorted(kept, key=float) if kept[s][0] is not None and kept[s][0] >= a0)
    assert first == [kept[s][0] - a0, kept[s][1]]


@check("SC1-m-kernel")
def _(kh, sid):
    _, kept = S.admission("x301", True, dict(S.DEBT_TOL), keep=("acute.debtH",))
    c = art("x30g", "rows.json", "row11", "closes")[1]
    assert c["session"] == "x301" and pt(sid, "N1") == kept[c["s_after"]][1] == c["debt_after"]


@check("SX2-m-kernel")
def _(kh, sid):
    ev = [{"minute": 120, "kind": "activity", "exercising": True},
          {"minute": 120, "kind": "setpath", "path": S.EXE_PATH, "value": "burpees"},
          {"minute": 150, "kind": "activity", "exercising": False},
          {"minute": 150, "kind": "setpath", "path": S.EXE_PATH, "value": None}]
    rows, _ = arm(ev, 181)
    assert pt(sid, 30.0) == rows[179]["HUNGER"]
