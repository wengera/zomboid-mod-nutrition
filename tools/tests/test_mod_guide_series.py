"""Tests for tools/mod_guide_series.py (Plan 14 Task 4 and its fix round 1): every series in docs/mod-guide/data.json
is non-empty, its provenance resolves, and its values are re-derived here independently, from a direct read of the
artifact or the dataset, a direct kernel call or a replay on the lupa host (tools/replay_live.py's own entry points),
or the vanilla model's formula functions, never through the series module's own builders.

The review's rules bind every series, and each has tests here that fail when it is broken:
- R-1: a multi-day kernel replay stays alive and under the dehydration bound over its plotted window, or names its
  death and ends there (`test_r1_*`);
- R-2: a live series is drawn only when the admission of the quantity it draws passes at a tolerance with a stated
  source (`test_r2_*`);
- R-3: a series' re-derivation checks a point past every change in its event schedule, and every point of a study
  series (`test_r3_*`, LATE below);
- R-4: a vanilla-model line ends at the model's death, and a qualitative study finding is a range, never a point
  (`test_r4_*`).

Beside them: the admission test, the reverse-coverage gate on the real tree, the UNMINTED guard, the trait ids (M-10),
the burpee bill (M-5), the guide foods' landed vector (#3182's check) and a mutation case (a kernel constant changed
on a scratch copy moves the data and fails --check).

The full build is the gate `python tools/mod_guide_data.py --check` (about a minute on a process pool); these tests
read the committed data file and never rebuild it whole.
"""
import io
import json
import math
import os
import re
import shutil
import sys
from contextlib import redirect_stderr, redirect_stdout

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
ADM = [v for v in DATA["validation"] if v.get("kind") == "admission"]
VIAB = {v["job"]: v for v in DATA["validation"] if v.get("kind") == "viability"}


def pt(sid, x):
    """The y of series sid at x (exact match on a category, nearest on a number)."""
    pts = SER[sid]["points"]
    if isinstance(x, str):
        return next(p[1] for p in pts if p[0] == x)
    return min(pts, key=lambda p: abs(p[0] - x))[1]


def xs_of(sid):
    return [p[0] for p in SER[sid]["points"]]


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


# the water every drinking scenario takes: 500 g every 2 h from 08:00 to 22:00 on the 07:00 clock (written here)
WATER_MIN = (60, 180, 300, 420, 540, 660, 780, 900)


def water(days, offset=0):
    return [{"minute": d * 1440 + m + offset, "kind": "autodrop", "g": 500.0} for d in range(days) for m in WATER_MIN]


# the plate every fed scenario eats, spelled here (a change to the module's PLATE moves the series and fails a check)
PLATE = ["Base.CannedBologneseOpen", "Base.Bread", "Base.Apple", "Base.Orange", "Base.Burger", "Base.TunaTinOpen"]


def plate(minute, size):
    return {"minute": minute, "kind": "meal", "size": size, "plate": list(PLATE)}


def arm(events, minutes, paths=(), **kw):
    """A fresh-record replay on the synthetic clock through replay_live.replay_arm (the display defaults); events at
    or past the last minute are left out."""
    kw.setdefault("hour_offset", 7.0)
    kw.setdefault("sleep_allowed", False)
    ev = sorted((e for e in events if e["minute"] < minutes), key=lambda e: e["minute"])
    rows, be = RL.replay_arm(ev, minutes=minutes, backend="server", rng="half", paths=paths, **kw)
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
    assert len(built) == 129 and len(S.PENDING_LIVE) == 10 and len(S.DROPPED) == 8
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
    checked = CHECKS[sid](kh)
    # R-3: past every change in the event schedule (LATE), and every point of a study series
    if SER[sid]["badge"] == "study":
        assert checked == "all", sid
    elif sid in LATE:
        assert checked and max(checked) >= LATE[sid], (sid, checked, LATE[sid])


# ---- R-1: viability ------------------------------------------------------------------------------------------------------

def test_r1_every_replay_series_names_a_job_with_a_recorded_viability():
    replayed = {sid for sid, s in SER.items() if s["badge"] == "kernel" and "water" in s["provenance"].get("inputs", {})}
    assert replayed <= set(S.SERIES_JOB)
    assert set(S.SERIES_JOB) <= set(SER)
    for sid, job in S.SERIES_JOB.items():
        assert job in VIAB, (sid, job)


@pytest.mark.parametrize("sid", sorted(S.SERIES_JOB))
def test_r1_each_replay_series_is_alive_and_hydrated_over_its_window(sid):
    v = VIAB[S.SERIES_JOB[sid]]
    if v["lethal"] is None:
        if not v["thirst_scenario"]:
            assert v["max_dehydPct"] <= S.DEHYD_BOUND, sid
        return
    # a death: named in the note, the series ends at it, and the dehydration bound holds to its onset
    assert v["series_death"] in (True, "allowed"), sid
    assert v["dmax_to_onset"] <= S.DEHYD_BOUND, sid
    assert max(xs_of(sid)) <= v["death_age"] / 24.0 + 1e-9, sid
    assert "lethal code %d" % v["lethal"][1] in SER[sid]["note"], sid


def test_r1_the_guard_refuses_a_lethal_or_a_dry_replay():
    alive = {"max_dehydPct": 1.0, "lethal": None, "death_age": None}
    S.assert_viable("ok", alive)
    with pytest.raises(D.ProvenanceError, match="dehydration"):
        S.assert_viable("dry", dict(alive, max_dehydPct=S.DEHYD_BOUND + 0.01))
    S.assert_viable("thirst", dict(alive, max_dehydPct=9.0), thirst=True)
    dead = {"max_dehydPct": 6.0, "dmax_to_onset": 1.0, "lethal": (100.0, 3), "death_age": 172.0}
    with pytest.raises(D.ProvenanceError, match="lethal code 3"):
        S.assert_viable("dead", dead)
    S.assert_viable("named", dead, death=True)
    with pytest.raises(D.ProvenanceError, match="names a death"):
        S.assert_viable("named", alive, death=True)
    assert S.until_death([[1.0, 5], [7.0, 6], [8.0, 7]], dead) == [[1.0, 5], [7.0, 6]]


def test_r1_a_fresh_fast_on_the_map_s_old_water_dies_of_dehydration(kh):
    # the review's C-1 finding reproduced: 600 g at 08, 12, 16 and 20 reaches lethal code 6 within six days
    ev = [{"minute": d * 1440 + m, "kind": "autodrop", "g": 600.0} for d in range(6) for m in (60, 300, 540, 780)]
    rows, be = arm(ev, 6 * 1440, ("fluids.dehydPct", "effects.lethal"))
    v = S.viability(rows, be.K)
    assert v["lethal"] is not None and v["lethal"][1] == 6
    with pytest.raises(D.ProvenanceError):
        S.assert_viable("old water", v)


# ---- R-2: admission per drawn quantity -----------------------------------------------------------------------------

def test_r2_every_admission_names_its_tolerance_source_and_what_it_draws():
    assert len(ADM) == len(S.ADMISSION_EXPECT)
    for v in ADM:
        assert {"kind", "key", "run", "quantity", "tolerance", "tolerance_source", "max_miss", "n", "admitted",
                "draws", "proves"} <= set(v), v["key"]
        assert v["tolerance_source"].startswith(("the run's own", "named here")), v["key"]
        assert v["admitted"] == all(v["max_miss"][f] <= v["tolerance"][f][1] for f in v["max_miss"]), v["key"]
        assert v["admitted"] == S.ADMISSION_EXPECT[v["key"]], v["key"]


def test_r2_every_drawn_live_series_is_admitted_and_every_dropped_one_is_not():
    live = [sid for sid, s in SER.items() if s["badge"] == "live"]
    for sid in live:
        recs = [v for v in ADM if sid in v["draws"]]
        assert recs, "%s is drawn by no admission" % sid
        if sid.startswith("S3b-m-live"):                                # drawn per run: days 0-4 from x341, x342
            assert all(v["admitted"] for v in recs if v["run"] in (S.RUN["x341"], S.RUN["x342"]))
        else:
            assert all(v["admitted"] for v in recs), sid
    for sid in set(S.DROPPED) - {"ST1-m-live", "S2d-m-drain"}:
        assert any(sid in v["draws"] and not v["admitted"] for v in ADM), sid


def test_r2_the_admission_grades_what_a_run_draws():
    rec, _ = S.admission("x361", False, dict(S.HUNGER_TOL))
    assert rec["admitted"] and rec["max_miss"]["HUNGER"] < 0.002
    stored = next(v for v in ADM if v["key"] == "x361:HUNGER")
    assert stored["max_miss"]["HUNGER"] == rec["max_miss"]["HUNGER"]
    rec, _ = S.admission("x364", False, dict(S.HUNGER_TOL))
    assert not rec["admitted"] and rec["max_miss"]["HUNGER"] > 0.002
    rec, _ = S.admission("x364", False, {"THIRST": ("abs", 0.002)})
    assert rec["admitted"] and rec["max_miss"]["THIRST"] < 0.002            # the stat S1c-m-live draws
    rec, _ = S.admission("x361", False, {"HUNGER": ("abs", 1e-6)})
    assert not rec["admitted"]


def test_r2_a_flipped_admission_fails_the_build(monkeypatch):
    monkeypatch.setitem(S.ADMISSION_EXPECT, "x37g:met", False)
    with pytest.raises(D.ProvenanceError, match="re-rule"):
        S.adm("x37g:met")


def test_r2_the_level_changes_of_x364_within_the_named_bound():
    rec = S.admission_levels("x364", False)
    assert rec["admitted"] and rec["n"]["level age (min)"] == 2
    assert rec["max_miss"]["level age (min)"] <= S.LEVEL_TOL_MIN


# ---- R-4: deaths and qualitative findings ----------------------------------------------------------------------------

def test_r4_the_vanilla_fast_lines_end_at_the_model_s_death():
    ev = [{"t_h": float(h), "kind": "drink", "fluid": "water", "litres": 0.25} for h in range(4, 72, 4)]
    sim = VM.simulate({"hours": 72.0, "dt_min": 1.0, "start": {"hunger": 0.0}, "events": ev})
    death = next(t for t, x in sim["health"] if x <= 0)
    t4 = -math.log(0.30) / VM.HUNGER_INCREASE / 3600.0
    assert death == pytest.approx(t4 + 100.0 / VM.health_loss_per_hour(4, 0), abs=2 / 60.0)   # 1-minute steps
    for sid in ("S2d-v-model-health", "S2d-v-model-weight"):
        assert max(xs_of(sid)) == pytest.approx(death / 24.0)
    assert SER["S2d-v-model-health"]["points"][-1][1] == 0.0
    assert SER["S2d-v-model-health"]["units"]["x"] == SER["S2d-m-mass"]["units"]["x"] == "game days"


QUALITATIVE = ("S4c-study-0078", "S3c-study")


@pytest.mark.parametrize("sid", QUALITATIVE)
def test_r4_a_qualitative_study_finding_is_a_range(sid):
    pts = SER[sid]["points"]
    assert len(pts) >= 2 and len({tuple(p) for p in pts}) == len(pts)


# ---- the UNMINTED guard ----------------------------------------------------------------------------------------------

def test_unminted_ids_are_left_out_until_minted_and_then_fail():
    ids = set(S._register())
    prov = S.vmodel("VM13", "JT1", ids=ids)
    assert "T2.1" not in prov["claims"] and "#2104" in prov["claims"]
    with pytest.raises(D.ProvenanceError, match="UNMINTED ids now in the register: T2.4"):
        S.vmodel("VM8", ids=ids | {"T2.4"})
    with pytest.raises(D.ProvenanceError, match="neither in the register nor in UNMINTED"):
        S.vmodel("VM9", ids=ids - {"#0155"})
    assert set(S.UNMINTED) == {"T2.1", "T2.2", "T2.3", "T2.4"}
    assert "T2.4" in VM.FORMULAS["VM8"]["claims"]


# ---- carries ---------------------------------------------------------------------------------------------------------

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


def test_a_plate_meal_carries_the_foods_whole_vectors(kh):
    # the plate (replay_live's meal `plate`): every key of the foods' table vectors summed and sized to the kcal
    be = RL.ServerReplay(user="admin", hour_offset=7.0, rng="half", sleep_allowed=False)
    vec = be.plate_vector(PLATE, 500.0)
    tot = {}
    for pz in PLATE:
        for k, v in be.NR.data.nutrients.get(pz).items():
            if isinstance(v, (int, float)):
                tot[k] = tot.get(k, 0.0) + v
    assert vec["calories"] == pytest.approx(500.0)
    for k in ("thiamine", "vitC", "proteins", "sodium"):
        assert vec[k] == pytest.approx(tot[k] * 500.0 / tot["calories"]) and vec[k] > 0
    with pytest.raises(ValueError):
        be.plate_vector(["Base.NotAFood"], 500.0)


# ---- the mutation case ---------------------------------------------------------------------------------------------

def test_a_kernel_constant_changed_on_a_scratch_copy_moves_the_data_and_fails_check(tmp_path):
    _, server_host, _ = RL._lua()
    lua = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
    scratch = tmp_path / "lua"
    shutil.copytree(lua, scratch)
    charts = {"H3": S.MAP_CHARTS["H3"]}
    out = str(tmp_path / "data.json")
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
# The re-derivations: each returns the x values it checked, or "all"
# ======================================================================================================================

CHECKS = {}

# R-3: the last change in each replayed series' event schedule (x in the series' own unit); a check must reach past it
LATE = {
    "H1-m-kernel": 0.01, "H2-m-fat": 1.0, "H2-m-lean": 1.0, "H2-m-total": 1.0, "S1a-m-kernel": 13.0,
    "S1b-m-kernel": 1.0, "S2a-m-kernel": 48.0, "S2d-m-mass": 1.0, "S3a-m-pool": 1.0, "S3a-m-grade": 1.0,
    "S3c-m-pool": 45.0, "S3b-m-kernel-U": 7.0, "S5b-m-strong-level": 2.0, "S5b-m-weak-level": 2.0,
    "S5b-m-none-level": 2.0, "S5b-m-gaunt-weight": 2.0, "S5b-m-overfat-weight": 2.0, "S5b-m-none-weight": 2.0,
    "S5c-m-gaunt": 2.0, "S5c-m-none": 2.0, "S6a-m-day1": 9.0, "S6a-m-day14": 9.0, "S6b-m-bac": 2.0,
    "S6b-m-intox": 2.0, "S6b-m-hangover": 2.0, "S6c-m-kernel": 2.0, "SX2-m-kernel": 0.0, "S4c-m-kernel": 730.0,
    "S2d-v-model-weight": 0.0, "S4c-v-model": 730.0, "S2a-v-model": 36.0, "S1a-v-model": 13.0,
}


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
    assert "17.3 game minutes" in SER[sid]["note"]                      # m-1: 0.24 x 13000 / 3.0 a second
    return [0.0, 6.0]


@check("H2-v-model")
def _(kh, sid):
    # the store from 0: +1500 a day against 0.016 x 86400 = 1382.4 burnt; its peak first passes 1000 on the third day
    assert pt(sid, 1.0) == 80.0 and pt(sid, 2.0) == 80.0 and pt(sid, 3.0) > 80.0
    return [1.0, 2.0, 3.0]


@check("H3-v-model-x1", "S4a-v-model-x1")
def _(kh, sid):
    sets = int(365 * 24 / 8.4) + 1                                       # one every 8.4 h from hour 0
    xp = 37500 + 360 * sets
    assert xp == 412980 and VM.level_for_xp(xp) == 9 == pt(sid, 365.0)
    return [365.0]


@check("H3-v-model-x15")
def _(kh, sid):
    n = math.ceil((487500 - 37500) / 540.0)                              # sets to level 10 at 540 XP a set
    day = math.ceil((n - 1) * 8.4 / 24.0)
    assert pt(sid, day) == 10 and pt(sid, day - 1) == 9
    return [day]


@check("S4a-v-model-x07")
def _(kh, sid):
    assert pt(sid, 365.0) == VM.level_for_xp(37500 + 252 * (int(365 * 24 / 8.4) + 1))
    return [365.0]


@check("S4b-v-model")
def _(kh, sid):
    pts = SER[sid]["points"]
    assert pt(sid, 0.0) == 5 and pt(sid, 10.0) >= 9
    # m-4: each point is its week's minimum, so the rust dip after the cap (from about day 340) shows within year 1
    first9 = next(x for x, lv in pts if x > 292 / 365.0 and lv < 10)
    assert first9 <= 345 / 365.0
    return [first9, 10.0]


@check("S4c-v-model")
def _(kh, sid):
    # the second year: the first rust step 48.6 days after the last set, then 1 XP a 1200-unit bucket (1.2 a day)
    xp = 412980 - math.floor((365 - 48.6) * 1440 / 1200)
    assert VM.level_for_xp(xp) == 9 == pt(sid, 730.0)
    assert pt(sid, 910.0) == 10                                          # 180 days back at 360 a set
    return [730.0, 910.0]


@check("S5b-v-model-level")
def _(kh, sid):
    first = (20000 + 50000) / 1440.0                                     # the rust timer from -50 000 to 20 000
    assert round(first, 1) == 48.6
    assert pt(sid, 48.0) == 5 and pt(sid, 49.0) == 4
    return [49.0]


@check("SS1-v-model")
def _(kh, sid):
    assert pt(sid, 20.0) == 9 and pt(sid, 0.0) == 4                     # no sets: rust takes 5 to 4 in the year
    return [0.0, 20.0]


@check("S1a-v-model")
def _(kh, sid):
    assert pt(sid, 1.0) == 0.0                                            # the tin at 08:00 clamps to 0
    assert pt(sid, 1.0 / 6) == pytest.approx(h_after(0.0, 600), abs=1e-12)
    # after the 20:00 tin (x 13): HUNGER at 13 h less 0.18, clamped; the 24 h point rises from it at the idle rate
    assert pt(sid, 24.0) > pt(sid, 13.0)
    return [1.0, 13.0, 24.0]


@check("S1b-v-model")
def _(kh, sid):
    assert pt(sid, 36.0) == VM.moodle_level(h_after(0, 36 * 3600), (0.15, 0.25, 0.45, 0.70)) == 4
    assert pt(sid, 34.0) == 3
    return [36.0]


@check("S1c-v-model")
def _(kh, sid):
    assert pt(sid, 24.0) == pytest.approx(8.0e-6 * 86400)
    return [24.0]


@check("ST1-v-model")
def _(kh, sid):
    assert pt(sid, 10.0) == pytest.approx(8.0e-6 * 36000)
    return [10.0]


@check("S2a-v-model")
def _(kh, sid):
    # the 20:00 eat takes HUNGER to 0 and fills 0.24 x 13000 = 3120 units, 1040 game seconds at 3 a second
    assert pt(sid, 30.0) == pytest.approx(h_after(0.0, 30 * 3600 - 1040), abs=1e-9)
    h36 = h_after(0.0, 36 * 3600 - 1040)
    assert pt(sid, 36.0) == pytest.approx(max(0.0, h36 - 0.24), abs=1e-9)   # the refeed at 08:00
    return [30.0, 36.0]


@check("S2c-v-model", "S5c-v-model", "S6c-v-model")
def _(kh, sid):
    want = 0.0 if sid == "S2c-v-model" else 1.0
    assert all(p[1] == want for p in SER[sid]["points"])
    return xs_of(sid)


@check("S2d-v-model-health")
def _(kh, sid):
    t4 = -math.log(1 - 0.70) / K_IDLE / 3600                            # 34.84 h to HUNGRY 4
    per_h = 0.0165 / 50 * 120 * 90                                        # 3.564 a game hour at DayLength 4
    assert pt(sid, 50.0 / 24) == pytest.approx(100 - per_h * (50 - t4), abs=0.1)
    return [50.0 / 24]


@check("S2d-v-model-weight")
def _(kh, sid):
    # from the 800 kcal start the store reaches 0 (the loss threshold at 80 kg, (80 - 70) x 30 floored at 0) after
    # 800 / 0.016 s; then the loss runs 8.5e-6 x |cal| / 2500 kg a second with |cal| = 0.016 s': by hand, day 1
    pts = SER[sid]["points"]
    assert pts[0] == [0.0, 80.0]
    s1 = 86400.0 - 800.0 / 0.016
    w1 = 80.0 - 8.5e-6 * 0.016 / 2500.0 * s1 * s1 / 2.0
    assert pts[1][1] == pytest.approx(w1, abs=2e-3)
    assert pts[2][1] < pts[1][1] < 80.0
    return [0.0, 1.0, 2.0]


@check("S5a-v-model-weight")
def _(kh, sid):
    assert [p[1] for p in SER[sid]["points"]] == [80.0, 105.0, 95.0, 70.0, 60.0, 70.0]
    return xs_of(sid)


@check("S5a-v-model-level")
def _(kh, sid):
    assert [p[1] for p in SER[sid]["points"]] == [5, 9, 0, 5, 0, 3]
    return xs_of(sid)


@check("S6a-v-model")
def _(kh, sid):
    assert all(p[1] == pytest.approx(-10 / 100 * 0.25) for p in SER[sid]["points"])
    return xs_of(sid)


@check("S6b-v-model")
def _(kh, sid):
    assert pt(sid, 1.0) == pytest.approx(400 * 0.05 * 0.3)
    decay = 0.0042 * 120 * 90                                            # 45.36 a game hour
    assert pt(sid, 1.0 + 5 / 60.0) == pytest.approx(6.0 - decay * 5 / 60.0, abs=1e-6)
    assert pt(sid, 2.0) == pytest.approx(6.0)
    return [1.0, 2.0]


@check("SB2-v-model")
def _(kh, sid):
    assert [p[1] for p in SER[sid]["points"]] == [1, 0, 1]               # 90 and 85 kg Overweight, 80 kg none
    return xs_of(sid)


@check("SX1-v-model")
def _(kh, sid):
    assert pt(sid, "idle") == pytest.approx(0.016 * 3600) and pt(sid, "running") == pytest.approx(0.13 * 3600)
    return xs_of(sid)


@check("SX2-v-model")
def _(kh, sid):
    h0 = float(re.search(r"\((\d\.\d+)\)", SER[sid]["note"]).group(1))
    assert pt(sid, 0.0) == pytest.approx(h_after(h0, 1800), abs=1e-4)
    return [0.0]


# ---- datasets: the files read directly ------------------------------------------------------------------------------

def _food_rec(pz):
    with open(os.path.join(REPO, "data", "food-nutrients.json"), encoding="utf-8") as fh:
        return next(i for i in json.load(fh)["items"] if i["pz_id"] == pz)


FOODS = (("Apple", "Base.Apple"), ("Bread", "Base.Bread"), ("Bolognese", "Base.CannedBologneseOpen"),
         ("Burger", "Base.Burger"), ("Tuna", "Base.TunaTinOpen"))


@check("H4-m-kcal", "H4-m-carb", "H4-m-fat", "H4-m-pro", "SN1-m-vitC", "SN1-m-fibre", "SN1-m-iron", "SN1-m-sodium")
def _(kh, sid):
    field = {"kcal": "calories", "carb": "carbs", "fat": "lipids", "pro": "proteins", "vitC": "vitC",
             "fibre": "fibre", "iron": "iron", "sodium": "sodium"}[sid.split("-")[-1]]
    assert SER[sid]["points"] == [[lab, _food_rec(pz)["per_item"][field]] for lab, pz in FOODS]
    return xs_of(sid)


@check("H4-v-kcal", "H4-v-carb", "H4-v-fat", "H4-v-pro")
def _(kh, sid):
    field = {"kcal": "Calories", "carb": "Carbohydrates", "fat": "Lipids", "pro": "Proteins"}[sid.split("-")[-1]]
    with open(os.path.join(D.INSTALL, "media", "scripts", "generated", "items", "food.txt"), encoding="utf-8",
              errors="replace") as fh:
        text = fh.read()
    for lab, pz in FOODS:
        block = re.search(r"\bitem %s\s*\{(.*?)\n\s*\}" % pz.split(".")[1], text, re.S).group(1)
        m = re.search(r"^\s*%s\s*=\s*([-\d.]+)" % field, block, re.M)
        assert pt(sid, lab) == float(m.group(1)), (sid, lab)
    return xs_of(sid)


# ---- live series: the artifact read directly -------------------------------------------------------------------------

@check("S2d-v-live-weight")
def _(kh, sid):
    s = art("scen", "scenario-nutrition_3day_fast.json", "test", "samples")
    assert SER[sid]["points"] == [[(x["worldAge"] - s[0]["worldAge"]) / 24, x["weight"]] for x in s]
    assert "started at 0" in SER[sid]["note"]                            # m-9: the store the control began from
    return xs_of(sid)


@check("S3b-m-live-U", "S3b-m-live-B")
def _(kh, sid):
    leaf = "server_U" if sid.endswith("U") else "moodLast_b"
    days = art("x34r", "rows.json", "row13", "days", "days")
    assert [p[1] for p in SER[sid]["points"]] == [days[str(d)][leaf] for d in range(5)]
    assert {days[str(d)]["session"] for d in range(5)} == {"x341", "x342"}
    return xs_of(sid)


@check("S5a-m-live-lean", "S5a-m-live-fat", "S5a-m-live-weight", "S5a-m-live-level")
def _(kh, sid):
    v = art("x436", "creation.json", "verdicts")

    def leaf(c):
        b, x = v["36_%s_body" % c]["observed"], v["36_%s_xp" % c]["observed"]
        return {"lean": b["record"]["lm"], "fat": b["record"]["fm"], "weight": b["derived"]["mass"],
                "level": x["client_level"]}[sid.split("-")[-1]]
    assert [p[1] for p in SER[sid]["points"]] == [leaf(c) for c in "abcdef"]
    return xs_of(sid)


@check("S5c-m-live")
def _(kh, sid):
    v = art("x436", "creation.json", "verdicts")
    assert [p[1] for p in SER[sid]["points"]] == [v["36_%s_hunger" % c]["observed"]["es"] for c in "def"]
    return xs_of(sid)


@check("S6c-m-live", "SC1-m-live-debt")
def _(kh, sid):
    closes = art("x30g", "rows.json", "row11", "closes")
    assert [p[1] for p in SER[sid]["points"]] == [c["debt_after"] for c in closes]
    return list(range(len(closes)))


@check("SC1-m-live-booked")
def _(kh, sid):
    n = art("x30g", "rows.json", "row11", "nights")
    assert SER[sid]["points"] == [[x["label"], x["booked_h"]] for x in n]
    return xs_of(sid)


@check("SE1-m-live-liquid", "SE1-m-live-fill")
def _(kh, sid):
    rows = art("x363", "minute-ring-admin-1.json", "rows_list")
    key = "stomach.liquid" if sid.endswith("liquid") else "stomachFill"
    a0 = rows[0]["age"]
    assert SER[sid]["points"] == [[(r["age"] - a0) * 60.0, r[key]] for r in rows if r.get(key) is not None][::5]
    return xs_of(sid)


@check("SH1-m-live")
def _(kh, sid):
    r = art("x36g", "grade.json", "sessions", "x361", "readings", "readings")
    assert SER[sid]["points"] == [[650.0, r["C650_request_vs_anchor"]["live_min"]],
                                  [400.0, r["C400_held_vs_180"]["live_min"]]]
    return xs_of(sid)


@check("S1b-m-live")
def _(kh, sid):
    ch = art("x36g", "grade.json", "sessions", "x364", "readings", "ring_levels", "changes")
    first = art("x364", "start.json", "rec", "firstSeen")
    assert SER[sid]["points"] == [[c["age"] - first, c["to"]] for c in ch]
    assert [round(p[0], 2) for p in SER[sid]["points"]] == [8.37, 20.86]   # the map's 8.37 h and 20.86 h
    return xs_of(sid)


@check("S1c-m-live")
def _(kh, sid):
    rows = []
    for page in (1, 721, 1441):
        rows += art("x364", "minute-ring-admin-%d.json" % page, "rows_list")
    first = art("x364", "start.json", "rec", "firstSeen")
    want = [[r["age"] - first, r["THIRST"]] for r in rows if r["age"] >= first][::10]
    assert SER[sid]["points"] == want
    return xs_of(sid)


@check("ST2-m-live-na")
def _(kh, sid):
    by = art("x28g", "rows.json", "sodium", "by_day")
    assert [p[1] for p in SER[sid]["points"]] == [by[str(d)]["na_change_per_24h"] for d in range(1, 6)]
    return xs_of(sid)


@check("SD1-m-live")
def _(kh, sid):
    b = art("x161b", "body.json")
    h0, h1 = b["health_reads"][53]["overall"], b["health_reads"][70]["overall"]
    rate = b["summaries"]["I"]["health"]["per_game_h"]
    (x0, y0), (x1, y1) = SER[sid]["points"]
    assert (y0, y1) == (h0, h1)                                           # I-6: the measured span alone
    assert (x1 - x0) * 24.0 == pytest.approx((h0 - h1) / -rate)
    return xs_of(sid)


@check("SX1-m-live")
def _(kh, sid):
    sets = art("x37g", "grade.json", "sessions", "x371", "sets")
    burpees = [b["billed"] for s in sets for b in s["bills"] if b["type"] == "burpees"]
    assert pt(sid, "burpees") == burpees[0] * 80.0 == 600.0
    return xs_of(sid)


@check("SV1-m-live")
def _(kh, sid):
    rows = art("x401", "accept.json", "verdicts", "OF", "observed", "rows")
    assert SER[sid]["points"] == [[r["server_mass"], r["levels"]] for r in rows]
    return xs_of(sid)


# ---- study series: the register's value cell, every point ------------------------------------------------------------

@check("S2b-study-1613")
def _(kh, sid):
    a, b = map(float, re.match(r"([\d.]+) vs ([\d.]+) MJ", science_value("S1613")).groups())
    assert SER[sid]["points"] == [["day 2", a / b]]
    return "all"


@check("S2b-study-1614")
def _(kh, sid):
    v = science_value("S1614")
    assert "7% greater on day 2" in v and "not different on day 3" in v
    assert SER[sid]["points"] == [["day 2", 1.07], ["day 3", 1.0]]
    return "all"


@check("S2c-study")
def _(kh, sid):
    assert "~100 kcal/day per kg" in science_value("S1254")
    pts = SER[sid]["points"]
    assert pts[0] == [0.0, 0.0] and pts[1][1] == pytest.approx(pts[1][0] * 95.0 / 0.76)
    assert pts[1][0] == max(xs_of("S2c-m-kernel"))
    return "all"


@check("S3a-study-0224", "S3a-study-0225", "SD2-study")
def _(kh, sid):
    sci = {"S3a-study-0224": "S0224", "S3a-study-0225": "S0225", "SD2-study": "S0225"}[sid]
    days = float(re.search(r"(\d+) days", science_value(sci)).group(1))
    want = [["vitC", days]] if sid == "SD2-study" else [[days, 0.15]]
    assert SER[sid]["points"] == want
    if sci == "S0225":
        assert "by construction" in SER[sid]["note"] and SER[sid]["label"].startswith("Padayatty 2016")
    return "all"


@check("S3c-study")
def _(kh, sid):
    assert "within one week" in science_value("S0229")
    assert SER[sid]["points"] == [[45.0, 0.15], [52.0, 0.15]]
    return "all"


@check("S4b-study")
def _(kh, sid):
    v = science_value("S1915")
    assert "25.0 kg/m2" in v
    P = kh.K.strength.DEFAULTS
    H = float(kh.K.HEIGHT_M)
    F = (25.0 - 6.3 * (1.80 - H)) * H * H                                # S1915's normalisation undone at the mod's height
    L = float(kh.K.strength.level(F, 1.0, P.Tmax, P))
    assert SER[sid]["points"] == [[0.0, pytest.approx(L, rel=1e-12)], [10.0, pytest.approx(L, rel=1e-12)]]
    return "all"


@check("S4c-study-0618")
def _(kh, sid):
    v = science_value("S0618")
    assert "−5 to −15 %" in v and "<8 wk" in v
    R = float(kh.K.strength.DEFAULTS.R)
    L365 = pt("S4c-m-kernel", 365)
    S365 = 1 + (L365 - 5) * (R - 1) / 5
    lv = [5 + 5 * (f * S365 - 1) / (R - 1) for f in (0.95, 0.85)]
    assert SER[sid]["points"] == [[449, pytest.approx(lv[0])], [449, pytest.approx(lv[1])], [786, L365]]
    assert "regains more slowly" in SER[sid]["note"]                     # I-5
    return "all"


@check("S4c-study-0078")
def _(kh, sid):
    assert "strength remained elevated" in science_value("S0078")
    assert SER[sid]["points"] == [[505, 5.0], [505, pt("S4c-m-kernel", 365)]]   # I-4: a range above baseline
    return "all"


@check("S6c-study")
def _(kh, sid):
    assert "(22%)" in science_value("S1566")
    assert SER[sid]["points"] == [[2.0, 1.22], [2.0 + 16.0 / 24.0, 1.22]]    # m-2: the waking day after the night
    return "all"


@check("SH1-study-1247")
def _(kh, sid):
    v = science_value("S1247")
    mins = [float(x) for x in re.findall(r"(\d+) \+/- \d+ min", v)]
    assert SER[sid]["points"] == [[k, m] for k, m in zip((190.0, 400.0, 825.0), mins)]
    return "all"


@check("SH1-study-1248")
def _(kh, sid):
    lo, hi = map(float, re.match(r"(\d+)-(\d+) min", science_value("S1248")).groups())
    assert SER[sid]["points"] == [[650.0, lo], [650.0, hi]]
    return "all"


@check("SH2-study")
def _(kh, sid):
    six, three = map(float, re.search(r"hunger AUC (\d+) \+/- \d+ mm.24 h on six meals vs (\d+)",
                                      science_value("S1608")).groups())
    assert SER[sid]["points"] == [["three meals", 1.0], ["six meals", six / three]]
    return "all"


# ---- kernel series: a direct kernel call or a replay -------------------------------------------------------------------

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


@check("H3-m-level", "S4a-m-perfect", "S4a-m-lowprotein", "S4a-m-deficit", "S4b-m-level", "SS1-m-kernel")
def _(kh, sid):
    sched = {"S4a-m-lowprotein": (20.0, 0.8, 260.0), "S4a-m-deficit": (20.0, 2.0, -500.0),
             "SS1-m-kernel": (3.0, 1.6, 260.0)}.get(sid, (20.0, 2.0, 260.0))
    n = 365 if sid == "SS1-m-kernel" else 28
    _, L = days_of(kh, [(n,) + sched])
    x = 3.0 if sid == "SS1-m-kernel" else (28 / 365.0 if sid == "S4b-m-level" else n)
    assert pt(sid, x) == L
    return [x]


@check("S4c-m-kernel")
def _(kh, sid):
    # past both changes: day 400 (stopped) and day 800 (retraining)
    _, L400 = days_of(kh, [(365, 20.0, 2.0, 260.0), (35, 0.0, 1.2, 0.0)])
    _, L800 = days_of(kh, [(365, 20.0, 2.0, 260.0), (365, 0.0, 1.2, 0.0), (70, 20.0, 2.0, 260.0)])
    assert pt(sid, 400) == L400 and pt(sid, 800) == L800
    return [400, 800]


@check("H3-m-written")
def _(kh, sid):
    K = kh.K
    b = body_new(kh)
    P = K.strength.DEFAULTS
    w = K.strength.heldLevel(K.strength.level(b.lm, b.N0, b.T, P), None)[0]
    for _ in range(200):
        K.strength.day(b, 20.0, 2.0, 260.0, 2600.0, 0.0, P, 1.0)
        w = K.strength.heldLevel(K.strength.level(b.lm, b.N0, b.T, P), w)[0]
    assert pt(sid, 200) == w
    return [200]


@check("S4b-m-cap")
def _(kh, sid):
    K = kh.K
    P = K.strength.DEFAULTS
    b = body_new(kh)
    assert all(p[1] == float(K.strength.level(b.Fc, b.N0, P.Tmax, P)) for p in SER[sid]["points"])
    return xs_of(sid)


@check("SB1-m-def-rest", "SB1-m-def-train", "SB1-m-sur-rest", "SB1-m-sur-train")
def _(kh, sid):
    sched = {"SB1-m-def-rest": (0.0, 1.2, -500.0), "SB1-m-def-train": (12.0, 2.0, -500.0),
             "SB1-m-sur-rest": (0.0, 1.2, 500.0), "SB1-m-sur-train": (12.0, 2.0, 500.0)}[sid]
    b, _ = days_of(kh, [(60,) + sched])
    assert pt(sid, 60) == float(b.lm) + float(b.lx)
    return [60]


@check("SB2-m-kernel")
def _(kh, sid):
    # lean 76.5 kg, fat 13.5: the fat index 13.5 / 2.89 x 52.02 / 76.5 is under the male cut 6 (#3856)
    assert 13.5 / 2.89 * 52.02 / 76.5 < 6 and pt(sid, "lean 90 kg") == 0
    b = kh.table({"lm": 59.5, "fm": 25.5, "fatT": 0, "thinT": 0})
    kh.K.traits.axes(b, 1)
    assert pt(sid, "soft 85 kg") == b.fatT == 1
    return xs_of(sid)


@check("SX1-m-kernel")
def _(kh, sid):
    assert pt(sid, "burpees") == 7.5 * 80 and pt(sid, "idle") == pytest.approx(1.3 * 80)
    return xs_of(sid)


@check("SV1-m-kernel")
def _(kh, sid):
    assert pt(sid, 1000) == kh.K.view.fullnessLevel(1000.0)
    assert max(xs_of(sid)) >= max(xs_of("SV1-m-live"))                   # m-3: the range covers the live rows
    return [1000]


@check("SD1-m-kernel")
def _(kh, sid):
    d, code = S.scurvy_drain(kh)
    assert code == 2 and d == pytest.approx(1 / 100.8)                  # #3106: 0.00992063 a game minute
    assert pt(sid, 1.0) == pytest.approx(100 - d * 1440)
    return [1.0]


@check("SD2-m-marginal", "SD2-m-clinical")
def _(kh, sid):
    k = 0.047427999622147034                                              # NR_Data_Records vitC k
    if sid.endswith("marginal"):
        assert pt(sid, "vitC") == math.ceil(math.log(1 / 0.70) / k)
    else:
        assert pt(sid, "vitC") in (40, 41) and abs(math.log(1 / 0.15) / k - 40) < 1e-9
    assert "Left out" in SER[sid]["note"]
    return xs_of(sid)


@check("SH1-m-kernel")
def _(kh, sid):
    M = S._kt("test_satiety_meal_studies")
    C = S._kt("conftest")
    assert [p[1] for p in SER[sid]["points"]] == M.callahan(C.LuaHost())
    return xs_of(sid)


@check("ST2-m-kernel")
def _(kh, sid):
    days, _ = S._kt("test_sodium_balance").simulate(5, 0.0)
    assert pt(sid, 1) == days[0]["na_end"] and pt(sid, 5) == days[4]["na_end"] - days[3]["na_end"]
    return [1, 5]


@check("H1-m-kernel")
def _(kh, sid):
    rows, _ = arm(water(1), 1440)
    m = int(round(RL.request_minute(rows, 0.0)))
    assert pt(sid, 0.0) == rows[m - 1]["HUNGER"] >= 0.25
    rows, _ = arm(water(1) + [eat(m, "Base.CannedBologneseOpen")], m + 361)
    x = (m + 361) / 60.0 - m / 60.0                                       # the last row, k = m + 360
    assert SER[sid]["points"][-1] == [pytest.approx(x), rows[m + 360]["HUNGER"]]
    return [0.0, x]


@check("H2-m-fat", "H2-m-lean", "H2-m-total")
def _(kh, sid):
    ev = [plate(d * 1440 + m, 500.0) for d in range(2) for m in (0, 300, 660)] + water(2)
    rows, _ = arm(ev, 2880, ("body.fm", "body.lm", "body.lx"))
    r = rows[2879]
    want = {"fat": r["body.fm"], "lean": r["body.lm"] + r["body.lx"],
            "total": r["body.fm"] + r["body.lm"] + r["body.lx"]}[sid.split("-")[-1]]
    assert pt(sid, 2.0) == want
    return [2.0]


@check("S1a-m-kernel")
def _(kh, sid):
    rows, _ = arm([eat(m, "Base.TunaTinOpen") for m in (60, 300, 540, 780)] + water(1), 1440)
    assert pt(sid, 70 / 60.0) == rows[69]["HUNGER"] and pt(sid, 24.0) == rows[1439]["HUNGER"]
    return [70 / 60.0, 24.0]


@check("S1b-m-kernel")
def _(kh, sid):
    rows, _ = arm(water(2), 36 * 60, (S.SIG,))
    assert pt(sid, 36.0) == int(rows[-1][S.SIG] // 1000) % 10
    return [36.0]


@check("S1c-m-kernel", "ST1-m-kernel")
def _(kh, sid):
    rows, _ = arm([], 600)
    assert pt(sid, 10.0) == rows[599]["THIRST"]
    return [10.0]


@check("S2a-m-kernel")
def _(kh, sid):
    O = S._kt("test_replay_live_oracle")
    _, fast, days = O.fast_plans()
    ev = [plate(m, k) for m, k in sorted(fast.items())] + water(days, offset=480)
    end = 5520 + 50 * 60                                                 # 50 h after the last meal: past day 2's meals
    rows, _ = arm(ev, end, hour_offset=0.0)
    assert pt(sid, -12.0) == rows[5520 - 720 - 1]["HUNGER"] and pt(sid, 50.0) == rows[end - 1]["HUNGER"]
    return [-12.0, 50.0]


def _oracle_arm(plan, days, extra=(), player=None):
    O = S._kt("test_replay_live_oracle")
    ev = O.sleep_events(days) + [plate(m, k) for m, k in sorted(plan.items())] + water(days, offset=480) + list(extra)
    ev = [e for e in ev if e["minute"] < days * 1440]
    return RL.replay_arm(sorted(ev, key=lambda e: e["minute"]), minutes=days * 1440, backend="server", rng="half",
                         player=player, hour_offset=0.0, sleep_allowed=True)


@check("S2b-m-kernel")
def _(kh, sid):
    O = S._kt("test_replay_live_oracle")
    M = S._kt("test_satiety_meal_studies")
    fed, fast, days = O.fast_plans()
    man = {"weight": 70.0, "female": False}
    _, bf = _oracle_arm(fed, days, player=man)
    _, bx = _oracle_arm(fast, days, player=man)
    W = M.FAST_WARM_DAYS
    i_fed, i_fast = RL.intake_by_day(bf.eats), RL.intake_by_day(bx.eats)
    assert SER[sid]["points"] == [["day 2", i_fast[W + 2] / i_fed[W + 2]], ["day 3", i_fast[W + 3] / i_fed[W + 3]]]
    return "all"


@check("S2c-m-kernel")
def _(kh, sid):
    E = S._kt("test_replay_live_energy")
    M = S._kt("test_satiety_meal_studies")
    fm_ref = kh.call("body.create", None, None, kh.K.strength.DEFAULTS, 1)["fm"]
    out = []
    for dep in (0.0, 0.25):
        plan = {int(d * 1440 + hh * 60): ("maint" if d == 0 else "request") for d in range(E.S1254_DAYS)
                for hh in M.FAST_MEAL_H}
        extra = [{"minute": 2, "kind": "setpath", "path": "body.fm", "value": fm_ref * (1 - dep)}]
        _, be = _oracle_arm(plan, E.S1254_DAYS, extra, player={"female": False})
        by = RL.intake_by_day(be.eats)
        out.append(sum(by[d] for d in E.S1254_READ) / len(E.S1254_READ))
    assert pt(sid, fm_ref * 0.25) == out[1] - out[0]
    return "all"


@check("S2d-m-mass")
def _(kh, sid):
    rows, _ = arm(water(3), 3 * 1440, ("body.fm", "body.lm", "body.lx"))
    r = rows[-1]
    assert pt(sid, 3.0) == r["body.fm"] + r["body.lm"] + r["body.lx"]
    v = VIAB["j_s2d"]
    assert v["lethal"][1] == 3 and max(xs_of(sid)) == pytest.approx(v["death_age"] / 24.0)
    assert v["death_age"] - v["lethal"][0] == pytest.approx(100.0 / float(kh.K.effects.DRAIN_RATE[3]) / 60.0)
    return [3.0, max(xs_of(sid))]


@check("S3a-m-pool", "S3a-m-grade", "S3c-m-pool")
def _(kh, sid):
    # tuna carries no vitamin C: the pool decays exactly exp(-k t) from the first sight (ZOH), t days of drains
    k = float(kh.NR.data.records.REC.vitC.k)
    if sid == "S3a-m-grade":
        assert pt(sid, 30.0) == 3 and pt(sid, 50.0) == 4 and math.exp(-k * 30) < 0.45
        return [30.0, 50.0]
    if sid == "S3a-m-pool":
        assert pt(sid, 30.0) == pytest.approx(math.exp(-k * (30.0 - 1 / 1440.0)), rel=1e-9)
        return [30.0]
    # S3c: past the first orange (day 45): a replay of the diet to day 47 (the pool's tail drawn exactly)
    ev = [eat(d * 1440 + m, "Base.TunaTinOpen") for d in range(47) for m in (60, 300, 540, 780)] + water(47)
    ev += [eat(d * 1440 + 180, "Base.Orange") for d in range(45, 47)]
    rows, _ = arm(ev, 47 * 1440, ("nutrients.vitC.p",))
    assert pt(sid, 47.0) == rows[-1]["nutrients.vitC.p"] > pt(sid, 45.0)
    return [47.0]


@check("S3b-m-kernel-U")
def _(kh, sid):
    # the whole fortnight: unhappiness sits at its cap 30 until day 9, so only the later days see the rotation
    varied = ("Base.Bread", "Base.CannedBologneseOpen", "Base.Burger", "Base.Apple", "Base.Orange", "Base.TunaTinOpen")
    ev = [eat(d * 1440 + m, "Base.TunaTinOpen") for d in range(7) for m in (60, 300, 540, 780)]
    ev += [eat(d * 1440 + m, varied[(d * 4 + i) % 6]) for d in range(7, 14) for i, m in enumerate((60, 300, 540, 780))]
    rows, _ = arm(ev + water(14), 14 * 1440)
    assert pt(sid, 11.0) == rows[11 * 1440 - 1]["UNHAPPINESS"] < 30
    assert pt(sid, 14.0) == rows[-1]["UNHAPPINESS"]
    return [11.0, 14.0]


def _s5b_rows(name, minutes, paths, food=True):
    traits, perk = S.S5B[name]
    be = RL.ServerReplay(player={"traits": traits, "female": False}, hour_offset=7.0, rng="half",
                         sleep_allowed=False)
    be.p.st.perk = perk
    days = minutes // 1440 + 1
    ev = water(days) + ([plate(d * 1440 + m, "request") for d in range(days) for m in (60, 360, 780)] if food else [])
    ev = sorted((e for e in ev if e["minute"] < minutes), key=lambda e: e["minute"])
    return RL.run(be, RL.synthetic_ages(minutes), ev, list(paths), start_age=0.0)


@check("S5b-m-strong-level", "S5b-m-weak-level", "S5b-m-none-level")
def _(kh, sid):
    name = sid.split("-")[2]
    want = {"strong": 9, "weak": 1, "none": 5}[name]                     # the mod's start levels (#3855)
    rows = _s5b_rows(name, 3 * 1440, ("body.wroteL",))
    assert pt(sid, 0.0) == rows[0]["body.wroteL"] == want and pt(sid, 3.0) == rows[-1]["body.wroteL"]
    return [0.0, 3.0]


@check("S5b-m-gaunt-weight", "S5b-m-overfat-weight", "S5b-m-none-weight", "S5c-m-gaunt", "S5c-m-none")
def _(kh, sid):
    name = {"gaunt": "gaunt", "overfat": "overweight", "none": "none"}[sid.split("-")[2]]
    rows = _s5b_rows(name, 3 * 1440, ("body.fm", "body.lm", "body.lx", "body.energyState"))

    def y(r):
        return r["body.energyState"] if sid.startswith("S5c") else r["body.fm"] + r["body.lm"] + r["body.lx"]
    assert pt(sid, 0.0) == y(rows[0]) and pt(sid, 3.0) == y(rows[-1])
    return [0.0, 3.0]


@check("S6a-m-day1", "S6a-m-day14")
def _(kh, sid):
    if sid.endswith("day1"):
        ev = [{"minute": m, "kind": "drink", "fluid": "Coffee", "litres": 0.25} for m in (60, 300, 540)]
        ev += [plate(m, "request") for m in (60, 360, 780)] + water(1)
        rows, _ = arm(ev, 1440, ("acute.caf",))
        assert pt(sid, 10.0) == rows[599]["acute.caf"]
        return [10.0]
    # between cups the caffeine decays on the 5.0 h half-life (K.acute.CAF_THALF_H): 23:00 to 07:00 of day 14
    a, b = pt(sid, 16.0), pt(sid, 24.0)
    assert b == pytest.approx(a * 0.5 ** (8.0 / float(kh.K.acute.CAF_THALF_H)), rel=1e-3)   # the gut's tail
    return [16.0, 24.0]


@check("S6b-m-bac", "S6b-m-intox", "S6b-m-hangover")
def _(kh, sid):
    ev = [{"minute": m, "kind": "drink", "fluid": "Beer", "litres": 0.3} for m in (60, 80, 100, 120)] + water(1)
    rows, _ = arm(ev, 1440, ("acute.bac", "effects.intoxTarget", "acute.hang"))
    path = {"bac": "acute.bac", "intox": "effects.intoxTarget", "hangover": "acute.hang"}[sid.split("-")[-1]]
    assert pt(sid, 190 / 60.0) == rows[189][path] and pt(sid, 600 / 60.0) == rows[599][path]
    return [190 / 60.0, 10.0]


@check("S6c-m-kernel")
def _(kh, sid):
    ev = [{"minute": 16 * 60, "kind": "sleep", "asleep": True}, {"minute": 1440, "kind": "sleep", "asleep": False},
          {"minute": 1440 + 20 * 60, "kind": "sleep", "asleep": True},
          {"minute": 2880, "kind": "sleep", "asleep": False}]
    ev += [plate(d * 1440 + m, "request") for d in range(3) for m in (60, 360, 780)] + water(3)
    rows, _ = arm(ev, 2 * 1440 + 60, ("acute.debtH",), sleep_allowed=True)
    debt = rows[2 * 1440 + 59]["acute.debtH"]
    assert debt > 0
    assert pt(sid, (2 * 1440 + 60) / 1440.0) == float(kh.K.satiety.sleepFactor(debt))
    return [(2 * 1440 + 60) / 1440.0]


@check("SE1-m-kernel-fill")
def _(kh, sid):
    rec, kept = S.admission("x363", False, {"stomachFill": ("abs", 0.002)}, keep=("stomachFill",))
    a0 = art("x363", "minute-ring-admin-1.json", "rows_list")[0]["age"]
    s = sorted(kept, key=float)[10]
    assert pt(sid, (kept[s][0] - a0) * 60.0) == kept[s][1]
    return [(kept[s][0] - a0) * 60.0]


@check("SH2-m-kernel")
def _(kh, sid):
    r = S.j_sh2()
    assert pt(sid, "six meals") == r["six"] / r["three"]
    return xs_of(sid)


@check("SM1-m-kernel")
def _(kh, sid):
    eps = float(kh.K.hybrid.FLOOR_EPS)
    _, kept = S.admission("x343", False, S.mood_tol(eps), keep=("UNHAPPINESS",))
    a0 = art("x34r", "rows.json", "row13", "release", "from_age")
    first = SER[sid]["points"][0]
    s = next(s for s in sorted(kept, key=float) if kept[s][0] is not None and kept[s][0] >= a0)
    assert first == [kept[s][0] - a0, kept[s][1]]
    return [first[0]]


@check("SC1-m-kernel")
def _(kh, sid):
    _, kept = S.admission("x301", True, dict(S.DEBT_TOL), keep=("acute.debtH",))
    c = art("x30g", "rows.json", "row11", "closes")[1]
    assert c["session"] == "x301" and pt(sid, "N1") == kept[c["s_after"]][1] == c["debt_after"]
    return xs_of(sid)


@check("SX2-m-kernel")
def _(kh, sid):
    ev = [{"minute": 120, "kind": "activity", "exercising": True},
          {"minute": 120, "kind": "setpath", "path": S.EXE_PATH, "value": "burpees"},
          {"minute": 150, "kind": "activity", "exercising": False},
          {"minute": 150, "kind": "setpath", "path": S.EXE_PATH, "value": None}] + water(1)
    rows, _ = arm(ev, 181)
    assert pt(sid, 30.0) == rows[179]["HUNGER"]
    return [30.0]
