"""The declarative effects table (NR_Data_Effects.lua, NR.data.effects; Plan 5 Task 6).

The composer (NR_Kernel_Effects.lua, K.effects.compose) folds every matching row of this table into
record.effects, so these tests pin the table's shape against the engine's contract: every surface carries an
operator the composer folds and a clamp around its identity; every row's selector is one of the engine's six
kinds with a source that exists for it; every entry names a surface, a numeric magnitude and its science row;
the two vitamin D rows carry gated = "VITD_EFFECTS" (ruling 8) and the two adequacy exceptions carry bonus
(the global constraint); the rulings the table encodes (no POISON row, ruling 12; FOOD_SICKNESS and not
SICKNESS, T1-1; no omega-3 or iron-infection row, rulings 8 and 17). The band magnitudes are literals evaluated
at the band's lower edge (A2) and are recomputed here in Python doubles from the briefing's formulas. The file
is data, not a kernel: the labelling rule (every line with a number carries its row) is a source-text test, and
science_check --scan names every S id it cites.
"""
import csv
import math
import os
import re
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
DATA = os.path.join(SHARED, "NR_Data_Effects.lua")
RECORDS = os.path.join(SHARED, "NR_Data_Records.lua")
NUTRIENTS = os.path.join(SHARED, "NR_Data_Nutrients.lua")
REGISTER = os.path.join(REPO, "docs", "reference", "science.tsv")

OPS = {"mul", "add", "max", "min", "or"}
SELECTORS = {"grade", "rung", "band", "flag", "pe", "ea"}
CHANNELS = {"stat", "trait", "body", "event"}
BANDS = ["caf", "wd", "bac", "alc", "hang", "bg", "iuS", "debt", "iu", "dehyd", "hypo", "ex"]
BAND_MAX = {"caf": 16, "wd": 4, "bac": 1, "alc": 2, "hang": 1, "bg": 3, "iuS": 12, "debt": 2, "iu": 25,
            "dehyd": 8, "hypo": 3, "ex": 4}
FLAGS = {"anaemia", "allReplete", "refeedEvent", "frozen", "bgroupMax", "coldCredit", "boutVig"}
SURFACES = {"mNut", "rNut", "stressTarget", "unhappyTarget", "panicTarget", "foodSickTarget", "poisonTarget",
            "healMul", "bleedMul", "infectMul", "coldMul", "tempOffset", "tempHeat", "speedMul", "fOffNut",
            "bruise", "drain", "nightVision", "shortSighted"}


def _load(host, path):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@" + os.path.basename(path))()


@pytest.fixture(scope="module")
def eh(host):
    _load(host, NUTRIENTS)
    _load(host, RECORDS)
    _load(host, DATA)
    return host


def _arr(h, t):
    return [t[i] for i in range(1, len(t) + 1)]


def _surf(h):
    return h.py(h.G.NutritionRevamp.data.effects.SURF)


def _rows(h):
    """Every row as a dict with its list as a Python list of entry dicts."""
    out = []
    for row in _arr(h, h.G.NutritionRevamp.data.effects.ROWS):
        d = h.py(row)
        d["list"] = [h.py(e) for e in _arr(h, row.list)]
        if isinstance(d.get("at"), dict):
            d["at"] = (d["at"][1], d["at"][2])
        out.append(d)
    return out


def _entries(h):
    return [(r, e) for r in _rows(h) for e in r["list"]]


def _register():
    with open(REGISTER, encoding="utf-8") as fh:
        return {r["id"]: r for r in csv.DictReader(fh, delimiter="\t")}


# --- SURF ---------------------------------------------------------------------------------------------------

def test_the_surfaces_are_the_composers(eh):
    surf = _surf(eh)
    assert set(surf) == SURFACES
    assert "hungerMul" not in surf and "thirstMul" not in surf             # ruling 3
    assert "sicknessTarget" not in surf                                   # T1-1: FOOD_SICKNESS, never SICKNESS


def test_every_surface_has_an_op_an_identity_and_a_clamp_around_it(eh):
    for name, s in _surf(eh).items():
        assert s["op"] in OPS, name
        if s["op"] == "or":
            assert s["id"] is False, name
            assert "lo" not in s and "hi" not in s, name
            continue
        assert isinstance(s["id"], (int, float)), name
        assert s["lo"] <= s["id"] <= s["hi"], name
        if s["op"] == "mul":
            assert s["id"] == 1, name                                     # the Severity form 1 + (v - 1) sev
        if s["op"] in ("add", "max"):
            assert s["id"] == 0, name


def test_the_clamps_are_the_briefings(eh):
    s = _surf(eh)
    lohi = lambda k: (s[k]["lo"], s[k]["hi"])
    assert lohi("mNut") == (1.0, 2.0) and lohi("rNut") == (0.5, 1.3)
    assert lohi("stressTarget") == (0, 0.50) and lohi("unhappyTarget") == (0, 59) and lohi("panicTarget") == (0, 64)
    assert s["foodSickTarget"]["op"] == "max" and lohi("foodSickTarget") == (0, 85)   # T1-1: never >= 90 (#2356)
    assert lohi("poisonTarget") == (0, 30)
    assert lohi("healMul") == (0.5, 1.0) and lohi("bleedMul") == (1.0, 1.25) and lohi("infectMul") == (1.0, 2.3)
    assert lohi("coldMul") == (0.5, 3.0) and lohi("tempOffset") == (-0.5, 0.3) and lohi("tempHeat") == (0, 0.3)
    assert s["speedMul"]["op"] == "min" and lohi("speedMul") == (0.75, 1.0)
    assert lohi("fOffNut") == (0, 0.15) and lohi("bruise") == (0, 1) and lohi("drain") == (0, 1)


def test_the_machine_and_gated_surfaces(eh):
    s = _surf(eh)
    assert {k for k, v in s.items() if v.get("machine")} == {"drain", "nightVision"}
    assert {k for k, v in s.items() if v.get("sevMin") is not None} == {"shortSighted"}
    assert s["shortSighted"]["sevMin"] == 1                              # ruling 7


def test_the_constants(eh):
    t = eh.G.NutritionRevamp.data.effects
    assert t.VITD_EFFECTS is False                                        # ruling 8
    assert t.BRUISE_T0 == 0.05                                            # F4


# --- ROWS ---------------------------------------------------------------------------------------------------

def test_every_selector_is_in_the_engines_set_with_a_source_for_it(eh):
    order = set(_arr(eh, eh.G.NutritionRevamp.data.records.ORDER))
    for r in _rows(eh):
        on = r["on"]
        assert on in SELECTORS, r
        src = r["src"]
        if on in ("grade", "rung"):
            assert src in order, r
        elif on == "band":
            assert src in BAND_MAX, r
        elif on == "flag":
            assert src in FLAGS, r
        else:
            assert src == on, r
        at = r.get("at")
        if on == "flag" and src != "bgroupMax":
            assert at is None, r                                         # a boolean flag matches true
            continue
        lo, hi = at if isinstance(at, tuple) else (at, at)
        assert isinstance(lo, int) and isinstance(hi, int) and lo <= hi, r
        top = {"grade": 4, "rung": 3, "pe": 4, "ea": 3, "flag": 4}.get(on) or BAND_MAX[src]
        bottom = {"grade": 2, "rung": 1, "pe": 2, "flag": 3}.get(on, 1)
        assert bottom <= lo and hi <= top, r                             # flat at and above replete: no row at identity
        assert r["list"], r


def test_every_entry_has_a_channel_a_surface_a_number_and_a_row(eh):
    surf = _surf(eh)
    reg = _register()
    for r, e in _entries(eh):
        assert e["ch"] in CHANNELS, e
        assert e["s"] in surf, e
        assert not surf[e["s"]].get("machine"), e                         # the machines are their own functions
        assert isinstance(e["v"], (int, float)) and not isinstance(e["v"], bool), e
        assert re.fullmatch(r"S\d{4}", e.get("row", "")), e
        assert e["row"] in reg and reg[e["row"]]["status"] != "superseded", e
        if reg[e["row"]]["status"] == "open":
            assert e.get("gc") is True, e                                # an open row's magnitude is a game choice
        assert e.get("gc") in (None, True), e
        assert set(e) <= {"ch", "s", "v", "row", "gc", "bonus"}, e
    for r in _rows(eh):
        assert set(r) <= {"src", "on", "at", "list", "gated", "unless"}, r


def test_the_vitamin_d_rows_are_the_two_gated_rows(eh):
    gated = [r for r in _rows(eh) if r.get("gated") == "VITD_EFFECTS"]
    assert len(gated) == 2
    assert {(r["src"], r["on"], r["at"]) for r in gated} == {("vitD", "grade", 3), ("vitD", "grade", 4)}
    assert all({e["s"] for e in r["list"]} == {"unhappyTarget", "coldMul"} for r in gated)
    assert {r.get("gated") for r in _rows(eh)} == {None, "VITD_EFFECTS", "BalanceBonus"}
    vitd_grade = [r for r in _rows(eh) if r["src"] == "vitD" and r["on"] == "grade"]
    assert vitd_grade == gated                                          # no ungated vitamin D deficiency row


def test_the_five_bonus_entries_are_the_named_exceptions(eh):
    bonus = [(r, e) for r, e in _entries(eh) if e.get("bonus")]
    got = {(r["src"], e["s"], r.get("gated")) for r, e in bonus}
    assert got == {("allReplete", "rNut", "BalanceBonus"), ("coldCredit", "coldMul", None),
                   ("ex", "rNut", None), ("ex", "panicTarget", None), ("ex", "unhappyTarget", None)}
    assert all(e["bonus"] is True for _, e in bonus)
    ex = [e for r, e in bonus if r["src"] == "ex"]
    assert len(ex) == 12 and all(e["row"] in ("S0826", "S0932") for e in ex)
    assert [e["v"] for r, e in _entries(eh) if r["src"] == "boutVig"] == [0.95]
    assert not [e for r, e in _entries(eh) if r["src"] == "boutVig" and e.get("bonus")]


def test_the_rulings_the_table_encodes(eh):
    entries = _entries(eh)
    assert not [e for _, e in entries if e["s"] == "poisonTarget"]       # ruling 12: POISON 0 at every rung
    assert not [r for r, _ in entries if r["src"] == "efa"]              # ruling 8: no omega-3 row
    assert not [r for r, e in entries if e["s"] == "infectMul" and r["on"] != "pe"]   # ruling 17: protein-energy only
    sick = [e["v"] for _, e in entries if e["s"] == "foodSickTarget"]
    assert set(sick) == {30, 55, 85}                                     # T1-1
    assert max(sick) < 90
    unless = {(r["src"], r["at"], r["unless"]) for r in _rows(eh) if r.get("unless")}
    assert unless == {("iron", 3, "anaemia"), ("ex", 1, "boutVig"), ("ex", 2, "boutVig"),
                      ("ex", 3, "boutVig"), ("ex", 4, "boutVig")}
    trait = [(r["src"], r["at"], e["s"]) for r, e in entries if e["ch"] == "trait"]
    assert trait == [("vitA", 4, "shortSighted")]                        # D3


def test_every_ul_record_has_a_rung_one_row(eh):
    recs = eh.py(eh.G.NutritionRevamp.data.records.REC)
    with_ul = {k for k, r in recs.items() if r.get("ul") is not None}
    rung1 = {r["src"] for r in _rows(eh) if r["on"] == "rung" and r["at"] == (1, 3)}
    assert rung1 == with_ul
    rung2 = {r["src"] for r in _rows(eh) if r["on"] == "rung" and r["at"] == (2, 3)}
    reach2 = {k for k, r in recs.items() if r.get("chronic") is not None or r.get("acute") is not None}
    reach2 &= with_ul
    assert rung2 == reach2 == {"vitB6", "vitA", "vitD", "selenium", "iron"}
    rung3 = [r["src"] for r in _rows(eh) if r["on"] == "rung" and r["at"] == 3]
    assert rung3 == ["iron"]


# --- the magnitudes, recomputed -----------------------------------------------------------------------------

def _band_values(h, src, surface):
    out = {}
    for r, e in _entries(h):
        if r["src"] == src and r["on"] == "band" and e["s"] == surface:
            at = r["at"]
            for n in (range(at[0], at[1] + 1) if isinstance(at, tuple) else [at]):
                assert n not in out, (src, surface, n)
                out[n] = e["v"]
    return out


DEHYD_EDGE = [None, 1, 1.5, 2, 2.5, 3, 4, 6, 10]


def _d(b):
    kn = [(1, 0), (1.6, 0.35), (2.5, 0.70), (4, 1.20)]
    if b <= 1:
        return 0
    if b >= 4:
        return 1.2
    for (x0, y0), (x1, y1) in zip(kn, kn[1:]):
        if b <= x1:
            return y0 + (y1 - y0) * (b - x0) / (x1 - x0)


def test_the_dehydration_accrual_at_each_lower_edge(eh):
    got = _band_values(eh, "dehyd", "mNut")
    assert sorted(got) == [2, 3, 4, 5, 6, 7, 8]                           # band 1 (1 %) is d = 0: no row (S0894, the studied range starts at 1 %)
    for n, v in got.items():
        assert v == pytest.approx(1 + 0.30 * _d(DEHYD_EDGE[n]), abs=1e-12), n
    assert got[4] == 1.21 and got[2] == 1.0875                            # I-B2 / I-B2b


def test_the_fatigue_offset_and_the_heat_side_at_each_lower_edge(eh):
    f = _band_values(eh, "dehyd", "fOffNut")
    assert sorted(f) == [3, 4, 5, 6, 7, 8]
    for n, v in f.items():
        assert v == pytest.approx(0.06 + 0.04 * min(1, (DEHYD_EDGE[n] - 2) / 2), abs=1e-12), n
    heat = _band_values(eh, "dehyd", "tempHeat")
    assert sorted(heat) == [4, 5, 6, 7, 8]                               # band 3 (2 %) is 0: no row
    for n, v in heat.items():
        assert v == pytest.approx(0.3 * min(1, max(0, (DEHYD_EDGE[n] - 2) / 2)), abs=1e-12), n
    assert _band_values(eh, "dehyd", "stressTarget") == {n: 0.06 for n in range(2, 9)}
    assert _band_values(eh, "dehyd", "panicTarget") == {n: 7 for n in range(2, 9)}
    assert _band_values(eh, "dehyd", "speedMul") == {7: 0.85, 8: 0.85}


def test_the_caffeine_rows(eh):
    r = _band_values(eh, "caf", "rNut")
    p = _band_values(eh, "caf", "panicTarget")
    assert sorted(r) == sorted(p) == list(range(1, 17))
    zero = 0.3 * 107
    for n in range(1, 17):
        c = 50 * n
        sat = min(1, max(0, (c - zero) / (107 - zero)))
        assert r[n] == pytest.approx(1 - 0.15 * sat, abs=1e-15), n
        expect = 15 * c / 400 if c <= 400 else 15 + 49 * (c - 400) / 400
        assert p[n] == pytest.approx(expect, abs=1e-12), n
    assert r[1] == 0.9641522029372497                                    # I-B3c at 50 mg
    assert (p[2], p[8], p[10], p[12], p[16]) == (3.75, 15.0, 27.25, 39.5, 64.0)   # I-E1


def test_the_sleep_mood_rows(eh):
    p = _band_values(eh, "iuS", "panicTarget")
    u = _band_values(eh, "iuS", "unhappyTarget")
    assert sorted(p) == sorted(u) == list(range(1, 13))
    for n in range(1, 13):
        q = n * 0.125
        assert p[n] == pytest.approx(min(20, 14 * q), abs=1e-12), n
        assert u[n] == pytest.approx(25 * q / 1.5, abs=1e-12), n
    assert (p[2], p[4], p[8], p[12]) == (3.5, 7.0, 14.0, 20)            # I-E1 at 0.25 / 0.5 / 1.0 / 1.5 IU
    assert u[12] == 25.0 and u[2] == 4.166666666666667


def test_the_exercise_and_withdrawal_rows(eh):
    assert _band_values(eh, "ex", "panicTarget") == {n: pytest.approx(-11 * n / 4, abs=1e-12) for n in range(1, 5)}
    assert _band_values(eh, "ex", "unhappyTarget") == {n: pytest.approx(-13 * n / 4, abs=1e-12) for n in range(1, 5)}
    assert _band_values(eh, "ex", "rNut") == {n: pytest.approx(1 + 0.10 * n / 4, abs=1e-12) for n in range(1, 5)}
    assert _band_values(eh, "wd", "mNut") == {n: pytest.approx(1 + 0.20 * n / 4, abs=1e-12) for n in range(1, 5)}
    assert _band_values(eh, "wd", "unhappyTarget") == {n: pytest.approx(10 * n / 4, abs=1e-12) for n in range(1, 5)}


def test_the_healing_cold_and_drain_free_magnitudes(eh):
    by = {}
    for r, e in _entries(eh):
        by.setdefault((r["src"], r["on"], r.get("at")), {})[e["s"]] = e["v"]
    assert [by[("pe", "pe", n)]["healMul"] for n in (2, 3, 4)] == [0.92, 0.80, 0.74]
    assert [by[("pe", "pe", n)]["infectMul"] for n in (2, 3, 4)] == [1.15, 1.55, 2.30]
    assert by[("pe", "pe", 4)]["healMul"] == pytest.approx(1 / 1.35, abs=0.002)   # S0951: 45.2 / 60.9
    assert [by[("vitC", "grade", n)]["healMul"] for n in (3, 4)] == [0.85, 0.50]
    assert [by[("vitC", "grade", n)]["bleedMul"] for n in (3, 4)] == [1.10, 1.25]
    assert by[("vitC", "grade", 4)]["bruise"] == 1 / 2880                # I-F4
    assert by[("vitC", "grade", 4)]["coldMul"] == 1.15
    assert [by[("zinc", "grade", n)]["healMul"] for n in (3, 4)] == [0.92, 0.85]
    assert [by[("ea", "ea", n)]["coldMul"] for n in (1, 2, 3)] == [1.3, 2.2, 3.0]
    assert [by[("debt", "band", n)]["coldMul"] for n in (1, 2)] == [1.6, 2.5]
    assert [by[("vitD", "grade", n)]["coldMul"] for n in (3, 4)] == [1.03, 1.06]
    assert [by[("vitD", "grade", n)]["unhappyTarget"] for n in (3, 4)] == [2, 4]
    assert by[("iron", "grade", 4)]["tempOffset"] == -0.2                 # S1016
    assert by[("iron", "grade", 3)]["mNut"] == 1.11
    assert by[("anaemia", "flag", None)]["mNut"] == 1.25
    assert by[("hang", "band", 1)] == {"mNut": 1.15, "stressTarget": 0.10}
    assert [by[("alc", "band", n)]["rNut"] for n in (1, 2)] == [0.90, 0.80]
    assert by[("boutVig", "flag", None)]["rNut"] == 0.95
    assert [by[("bgroupMax", "flag", n)]["stressTarget"] for n in (3, 4)] == [0.03, 0.06]
    assert by[("bac", "band", 1)]["stressTarget"] == 0                   # never during (S0931)
    assert by[("bg", "band", 3)] == {"fOffNut": 0.10, "speedMul": 0.85, "tempOffset": -0.2}
    assert by[("bg", "band", 2)] == {"speedMul": 0.92}
    assert by[("iu", "band", (20, 25))] == {"speedMul": 0.90}
    assert by[("hypo", "band", (2, 3))] == {"speedMul": 0.85}
    assert by[("hypo", "band", 2)] == {"foodSickTarget": 55} and by[("hypo", "band", 3)] == {"foodSickTarget": 85}
    assert by[("refeedEvent", "flag", None)] == {"foodSickTarget": 55}


# --- the labelling rule as a tool check for this file -------------------------------------------------------

NUM = re.compile(r"(?<![A-Za-z_0-9.])\d")
SID = re.compile(r"\bS\d{4}\b")
LABEL = re.compile(r"\bS\d{4}\b|game choice|#\d{4}|no row needed")


def _code_and_comment(line):
    code = re.sub(r'"[^"]*"', '""', line)
    i = code.find("--")
    if i < 0:
        return code, ""
    return code[:i], line[line.find("--"):]


def _lines():
    with open(DATA, encoding="utf-8") as fh:
        return fh.read().splitlines()


def test_every_number_line_carries_a_label():
    bad = [(n, line) for n, line in enumerate(_lines(), 1)
           if NUM.search(_code_and_comment(line)[0]) and not LABEL.search(_code_and_comment(line)[1])]
    assert bad == []


def test_every_game_choice_names_an_open_row():
    reg = _register()
    bad = []
    for n, line in enumerate(_lines(), 1):
        code, comment = _code_and_comment(line)
        if "game choice" in comment and code.strip():
            if not any(reg.get(i, {}).get("status") == "open" for i in SID.findall(comment)):
                bad.append((n, line))
    assert bad == []


def test_every_cited_row_exists_and_an_open_one_is_labelled_open():
    reg = _register()
    for n, line in enumerate(_lines(), 1):
        for sid in SID.findall(line):
            assert sid in reg, (n, sid)
            assert reg[sid]["status"] != "superseded", (n, sid)
            if reg[sid]["status"] == "open":
                assert re.search(r"\bopen\b|game choice", line), (n, sid, line)


def test_science_check_scan_is_clean():
    out = subprocess.run([sys.executable, os.path.join(REPO, "tools", "science_check.py"), "--scan", DATA],
                         cwd=REPO, capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


def test_the_banner_says_not_a_kernel_file():
    assert _lines()[0].startswith("-- NR_Data_Effects.lua -- not a kernel file")
