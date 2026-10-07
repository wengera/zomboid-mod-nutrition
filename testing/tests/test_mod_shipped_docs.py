"""Plan 9 Task 2: the shipped docs, the manifest's release description and the version agreement."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "mod" / "NutritionRevamp"
MOD_INFO = MOD / "42.20.4" / "mod.info"
CORE = MOD / "common" / "media" / "lua" / "shared" / "NR_Core.lua"
PASS = MOD / "common" / "media" / "scripts" / "NR_ItemPass_Food.txt"

NEIGHBOURS = [
    "Nutrition Makes Sense", "StatsAPI", "Stat Tweaks Lib", "QualityCooking", "BeyondTen",
    "SomewhatTraitsCore", "GirthsTweaks", "EmergencyVomit", "SWMisc_Patches", "SkillRecoveryJournal",
    "simpleStatus", "Nutrition Tweaker Enhanced", "ApocalipseBR Nutrition Sync Fix", "Reasonable Nutrition",
    "Realistic Nutrition", "Evolving Traits World", "Tooltiplib", "MoodleFramework",
]

# The loader's mod.info branches test `contains` on the token (#0806), so none may sit inside a value.
KEY_TOKENS = ["name=", "id=", "description=", "poster=", "require=", "url=", "icon=", "pack=", "tiledef=",
              "versionMin=", "versionMax=", "modversion=", "incompatible=", "loadModAfter=", "loadModBefore=",
              "category=", "authors="]
FORBIDDEN_WORDS = ["require", "poster", "icon", "url"]


def mod_info():
    keys = {}
    for line in MOD_INFO.read_text(encoding="utf-8").split("\n"):
        if "=" in line:
            k, v = line.split("=", 1)
            keys[k] = v
    return keys


def test_the_three_shipped_docs_exist_and_are_not_empty():
    for name in ("README.md", "CHANGELOG.md", "COMPATIBILITY.md"):
        p = MOD / name
        assert p.is_file(), name
        assert p.read_text(encoding="utf-8").strip(), name


def test_the_release_notes_name_every_neighbour():
    text = (MOD / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## 1.0.0 — 2026-10-06" in text
    assert "### Compatibility" in text
    missing = [n for n in NEIGHBOURS if n not in text]
    assert missing == []


def test_the_compatibility_table_names_every_neighbour():
    text = (MOD / "COMPATIBILITY.md").read_text(encoding="utf-8")
    missing = [n for n in NEIGHBOURS if n not in text]
    assert missing == []


def test_the_description_is_one_line_short_and_clean():
    raw = MOD_INFO.read_text(encoding="utf-8")
    assert "\r" not in raw
    desc_lines = [l for l in raw.split("\n") if l.startswith("description=")]
    assert len(desc_lines) == 1
    desc = desc_lines[0][len("description="):]
    assert 0 < len(desc) <= 1000
    assert "Nutrition Makes Sense" in desc
    assert [t for t in KEY_TOKENS if t in desc] == []
    assert [w for w in FORBIDDEN_WORDS if w in desc.lower()] == []


def test_modversion_equals_the_lua_version():
    m = re.search(r'^\s*version\s*=\s*"([^"]+)"', CORE.read_text(encoding="utf-8"), re.M)
    assert m is not None
    assert mod_info()["modversion"] == m.group(1) == "1.0.0"


def test_the_self_report_sentinel_matches_the_pass_files_first_item():
    core = CORE.read_text(encoding="utf-8")
    m = re.search(r'itemPassSentinel\s*=\s*\{\s*fullType\s*=\s*"Base\.(\w+)",\s*calories\s*=\s*([0-9.]+)\s*\}', core)
    assert m is not None
    first = re.search(r"item\s+(\w+)\s*\{[^}]*?Calories\s*=\s*([0-9.]+)", PASS.read_text(encoding="utf-8"), re.S)
    assert first is not None
    assert (m.group(1), float(m.group(2))) == (first.group(1), float(first.group(2)))


def _core_runtime():
    lupa = __import__("pytest").importorskip("lupa")
    lua51 = getattr(lupa, "lua51", lupa)
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(CORE.read_text(encoding="utf-8"))
    return rt


def test_the_sentinel_read_answers_true_false_and_unread():
    rt = _core_runtime()
    nr = rt.globals().NutritionRevamp
    assert nr.itemPassActive() == "unread"                       # no instanceItem global
    rt.execute('instanceItem = function(t) return { getCalories = function(self) return 109.70999908447266 end } end')
    assert nr.itemPassActive() == "true"
    rt.execute('instanceItem = function(t) return { getCalories = function(self) return 55.0 end } end')
    assert nr.itemPassActive() == "false"
    rt.execute('instanceItem = function(t) return {} end')
    assert nr.itemPassActive() == "unread"                       # no getter
    rt.execute('instanceItem = function(t) error("boom") end')
    assert nr.itemPassActive() == "unread"                       # a raise
