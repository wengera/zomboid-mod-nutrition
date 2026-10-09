"""The soft cap shown as the mod's own Overfull moodle (Plan 11c Task 7, ruling 11c-25).

K.view.fullnessLevel(massG) reads 0..4 off K.satiety.discomfort over the stomach's comfortable maximum (730 g,
K.stomach.CAPACITY_MAX_G) and its full scale (1100 g, K.stomach.CAPACITY_HARD_G), in thirds of the 0-100 scale (a
labelled game choice on ruling 11c-8's inferences, S1250 and S1253). The mirror carries the stomach's whole mass,
both lanes, rounded to 1 g, as m.stomachMass, because the fill F (stomachFill) clamps at 1 at 730 g and so cannot
place a level above it. K.view.moodleClasses adds the seventh class, overfull, to the six K.view.classes reads. The
writer never writes CharacterStat.DISCOMFORT: a once-a-minute floor blinks every 2.5 s and vanishes asleep (ruling
11c-25), so the cap is shown and never blocks an eat.
"""
import glob
import math
import os
import re

import pytest

from .server_host import REPO
from . import test_writer_shape as W


def V(h):
    return h.K.view


def stomach(h, solid=None, liquid=0):
    buf = h.call("vector.new")
    for k, v in (solid or {}).items():
        buf[k] = v
    t = h.rt.table()
    t["buffer"] = buf
    if liquid is not None:
        t["liquid"] = liquid
    return t


META = {"mode": 1, "version": "v", "build": "b"}


def mirror(h, **rec):
    r = {"username": "a", "firstSeen": 1.0, "lastSeen": 2.0, "resets": 0, "dead": False}
    r.update(rec)
    return h.py(h.call("mirror.build", h.table(r), h.table(META)))


# --- the level ------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("mass,want", [
    (0, 0), (500, 0), (729, 0), (730, 0),          # at or under the comfortable maximum: no moodle
    (731, 1), (853, 1),                             # the first third: (853 - 730) / 370 = 33.2 %
    (854, 2), (976, 2),                             # 854 g reads 33.5 %, 976 g 66.5 %
    (977, 3), (1099, 3),                            # 977 g reads 66.8 %, 1099 g 99.7 %
    (1100, 4), (1100.5, 4), (5000, 4),              # the full scale and past it
])
def test_the_level_bands_and_their_edges(host, mass, want):
    assert V(host).fullnessLevel(mass) == want


def test_the_band_edges_sit_on_thirds_of_the_discomfort_scale(host):
    assert V(host).fullnessLevel(730 + 370 / 3 - 1e-6) == 1
    assert V(host).fullnessLevel(730 + 370 / 3 + 1e-6) == 2
    assert V(host).fullnessLevel(730 + 740 / 3 - 1e-6) == 2
    assert V(host).fullnessLevel(730 + 740 / 3 + 1e-6) == 3
    assert V(host).fullnessLevel(1100 - 1e-6) == 3
    assert host.py(V(host).OVERFULL_AT) == {1: pytest.approx(100 / 3), 2: pytest.approx(200 / 3), 3: 100}


@pytest.mark.parametrize("mass", [float("nan"), float("inf"), float("-inf"), -1, -5000, None, "900", True])
def test_a_non_finite_negative_or_non_number_mass_reads_zero(host, mass):
    assert V(host).fullnessLevel(mass) == 0


def test_the_level_reads_the_stomach_capacities(host):
    S = host.K.stomach
    assert S.CAPACITY_MAX_G == 730 and S.CAPACITY_HARD_G == 1100
    assert V(host).moodleTop("overfull") == 4


# --- the mirror -----------------------------------------------------------------------------------------------

def test_the_mirror_carries_the_whole_mass_of_both_lanes_rounded(host):
    s = stomach(host, {"water": 400.25, "proteins": 30.0, "carbs": 120.0, "lipids": 25.0, "fibre": 6.0,
                       "calories": 900.0, "ethanol": 10.0}, liquid=300.4)
    m = mirror(host, stomach=s, stomachFill=1)
    assert m["stomachMass"] == 882                   # 400.25 + 30 + 120 + 25 + 6 + 300.4 = 881.65, rounded
    assert m["stomachFill"] == 1                     # the fill clamps at 1 from 730 g; the moodle reads the mass
    assert isinstance(m["stomachMass"], (int, float))


def test_the_mirror_function_equals_the_mirrors_field_in_each_record_case(host):
    cases = [stomach(host, {"water": 400.25, "proteins": 30.0, "carbs": 120.0, "lipids": 25.0, "fibre": 6.0}, liquid=300.4),
             None, host.table({"liquid": 400.0}),
             stomach(host, {"water": float("nan")})]
    for s in cases:
        rec = {} if s is None else {"stomach": s}
        assert host.K.mirror.stomachMass(host.table({"stomach": s} if s is not None else {})) == mirror(host, **rec)["stomachMass"]
    assert host.K.mirror.stomachMass(cases[0] and host.table({"stomach": cases[0]})) == 882


def test_the_liquid_lane_counts_whole_not_at_its_satiety_fifth(host):
    m = mirror(host, stomach=stomach(host, {"water": 100.0}, liquid=1000.0))
    assert m["stomachMass"] == 1100
    assert V(host).fullnessLevel(m["stomachMass"]) == 4


def test_the_solid_lane_alone_and_a_missing_liquid_lane_that_reads_zero(host):
    m = mirror(host, stomach=stomach(host, {"water": 200.0, "carbs": 50.4}))
    assert m["stomachMass"] == 250
    m = mirror(host, stomach=stomach(host, {"water": 200.0, "carbs": 50.4}, liquid=None))
    assert m["stomachMass"] == 0                     # an absent lane is malformed (ruling C9-9)
    m = mirror(host, stomach=stomach(host, {"water": 200.0, "carbs": 50.6}, liquid=0))
    assert m["stomachMass"] == 251


def test_a_record_with_no_stomach_or_no_buffer_reads_zero_mass(host):
    assert mirror(host)["stomachMass"] == 0
    assert mirror(host, stomach=host.table({"liquid": 400.0}))["stomachMass"] == 0


def test_a_non_finite_mass_reads_zero(host):
    assert mirror(host, stomach=stomach(host, {"water": float("nan")}))["stomachMass"] == 0
    assert mirror(host, stomach=stomach(host, {}, liquid=float("inf")))["stomachMass"] == 0


def test_the_mirror_grows_by_one_number(host):
    m = mirror(host)
    assert "stomachMass" in m and "stomach" not in m
    assert all(isinstance(v, (str, int, float, bool)) for v in m.values())


# --- the classes the moodles read -----------------------------------------------------------------------------

SIX = ["energy", "hydration", "deficiency", "excess", "stimulant", "sleep"]


def test_moodle_classes_are_the_six_and_overfull(host):
    assert host.py(V(host).moodleClasses(None)) == dict({c: 0 for c in SIX}, overfull=0)
    c = host.py(V(host).moodleClasses(host.table({"acute_debtH": 13, "stomachMass": 1000})))
    assert c["sleep"] == 3 and c["overfull"] == 3
    assert host.py(V(host).classes(host.table({"stomachMass": 1000}))) == {c: 0 for c in SIX}  # the panel's six


def test_overfull_reads_the_mass_never_the_fill(host):
    c = host.py(V(host).moodleClasses(host.table({"stomachFill": 1, "stomachMass": 1100})))
    assert c["overfull"] == 4
    c = host.py(V(host).moodleClasses(host.table({"stomachFill": 1, "stomachMass": 700})))
    assert c["overfull"] == 0
    c = host.py(V(host).moodleClasses(host.table({"stomachFill": 1})))   # a pre-Task-7 mirror: no mass, no moodle
    assert c["overfull"] == 0


# --- never DISCOMFORT -----------------------------------------------------------------------------------------

def _code(src):
    src = re.sub(r"--\[(=*)\[.*?\]\1\]", "", src, flags=re.S)
    return "\n".join(line.split("--", 1)[0] for line in src.splitlines())


def test_no_mod_lua_names_the_discomfort_stat():
    lua = os.path.join(REPO, "mod", "NutritionRevamp")
    files = glob.glob(os.path.join(lua, "**", "*.lua"), recursive=True)
    assert len(files) > 40
    for p in files:
        with open(p, encoding="utf-8") as fh:
            code = _code(fh.read())
        assert "CharacterStat.DISCOMFORT" not in code, p
        assert re.search(r"[\"']DISCOMFORT[\"']", code) is None, p


def test_the_writer_never_sets_discomfort_at_a_full_stomach():
    h = W.boot()
    h.G.CharacterStat.DISCOMFORT = "DISCOMFORT"
    p = W.player(h)
    full = h.rt.eval("function() local b = NutritionRevamp.kernel.vector.new(); b.water = 900; b.carbs = 150; "
                     "return { buffer = b, liquid = 300 } end")()
    rec = W.record(h, stomachFill=1, stomach=full)
    for minute in range(1, 6):
        W.step(h, p, rec, minute)
    sets = list(p.st.sets.keys())
    assert "HUNGER" in sets                         # the writer ran
    assert "DISCOMFORT" not in sets
