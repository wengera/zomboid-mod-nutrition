"""Tests for the workshop mod inventory scan.

Two questions, one per half of the module: does a record carry the id **the game** resolves
(delegated wholesale to `mod_lint`, so the tests here pin the delegation and the record shape,
not the resolution rules -- `test_mod_lint.py` owns those), and do the script-file signals see
what the `.lua` regexes never could. Each synthetic fixture names the installed mod whose shape
it stands in for; the `skipUnless` block at the bottom pins the real folders slice 08's catalog
is written against.
"""
import datetime, json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import mod_inventory

# No CLI test here, unlike test_mod_lint.py: `mod_inventory.main()` writes the committed
# data/mod-inventory.json, and a test run must not silently rewrite repo data.

ITEM_SCRIPT = """\
module Base
{
    item DriedApple
    {
        DisplayName = Dried Apple,
        Type = Food,
        HungerChange = -10,
        Calories = 52,
        Carbohydrates = 14,
        Proteins = 0.3,
        Lipids = 0.2,
        DaysFresh = 90,
    }
    item DriedPear
    {
        DisplayName = Dried Pear,
        Type = Food,
    }
}
"""


def _write(d, rel, text):
    p = os.path.join(d, *rel.split("/")); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(text); return p


def _mod(d, name, files):
    """Build the mod folder `d/name` from {relative path: contents} and return it."""
    for rel, text in files.items():
        _write(d, name + "/" + rel, text)
    return os.path.join(d, *name.split("/"))


def test_version_folder_mod_info_beats_a_stale_copy_at_the_root():
    """LongTermPreservation4220 3774789651's lesson, as a fixture: the old scan read
    `<mod>/mod.info` only, so a stale root copy decided the id. B42 reads the version folder."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "LTP", {"42.20/mod.info": "name=Long Term Preservation\nid=SKITTLE_LTP\n"
                                                "author=Skittles\nrequire=\\Base,\\OtherMod\n",
                              "mod.info": "name=old\nid=LongTermPreservation4220\n",
                              "42.20/media/scripts/items/x.txt": ITEM_SCRIPT})
        m = mod_inventory.scan_mod(mod)
        assert m["mod_id"] == "SKITTLE_LTP"
        assert m["mod_id_fallback"] == "LTP"
        assert m["mod_info_at"] == "42.20/mod.info"
        assert m["version_dirs"] == ["42.20"]
        assert m["layout"] == "42.20"
        assert m["name"] == "Long Term Preservation" and m["author"] == "Skittles"
        # `require=` is the one non-scalar mod.info value: comma list, leading backslashes.
        assert m["require"] == ["Base", "OtherMod"]


def test_a_mod_with_no_mod_info_has_an_empty_id_not_a_folder_name():
    """3782784855/Skill Recovery Journal ships only `42.20.1/media`. The game cannot identify
    it (`workshop_index()` returns 229 for 230 folders) and neither may the inventory: an id
    invented from the folder name is a profile entry that silently matches nothing."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "Skill Recovery Journal", {"42.20.1/media/lua/shared/x.lua": "print(1)\n"})
        m = mod_inventory.scan_mod(mod)
        assert m["mod_id"] == ""
        assert m["mod_id_fallback"] == "Skill Recovery Journal"
        assert m["mod_info_at"] is None
        assert m["name"] == "?" and m["author"] == "?" and m["require"] == []
        assert m["stats"] == {"lua_shared": 1}, "42.20.1 must be walked, not skipped"


def test_three_part_version_folder_wins_over_a_two_part_one():
    """The bug this slice fixes: `42(?:\\.(\\d+))?` never matched `42.20.1`, and a string sort
    puts `42.9` above `42.20` anyway. Both answers come from `mod_lint.version_dirs` now."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "V", {"42.9/mod.info": "id=old\n",
                            "42.9/media/lua/shared/old.lua": "print(1)\n",
                            "42.20.1/mod.info": "id=live\n",
                            "42.20.1/media/lua/shared/new.lua": "print(2)\nprint(3)\n"})
        m = mod_inventory.scan_mod(mod)
        assert m["version_dirs"] == ["42.20.1", "42.9"]
        assert m["mod_id"] == "live" and m["mod_info_at"] == "42.20.1/mod.info"
        assert m["layout"] == "42.20.1"
        assert m["stats"] == {"lua_shared": 1}, "only the live folder's content is the mod"


def test_mod_info_and_media_in_common_are_the_fallback():
    """AutoCook/gasmask's shape: no version folder holds anything, `common/` does."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "C", {"common/mod.info": "id=C\n",
                            "common/media/scripts/items/x.txt": ITEM_SCRIPT})
        m = mod_inventory.scan_mod(mod)
        assert (m["mod_id"], m["layout"], m["mod_info_at"]) == ("C", "common", "common/mod.info")
        assert m["stats"] == {"script_files": 1}


def test_script_files_are_read_for_nutrition_keys_not_just_counted():
    """The signal `mod_inventory` never had: a pure content mod writes nutrition into item
    definitions, where no `.lua` regex can see it. `module Base` means these two items
    OVERRIDE vanilla ones; a mod writing `module <Own>` only adds."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "S", {"42/mod.info": "id=S\n", "42/media/scripts/items/x.txt": ITEM_SCRIPT})
        m = mod_inventory.scan_mod(mod)
        assert m["signals"]["script_nutrition"] == 6
        assert m["script_nutrition_keys"] == {"Calories": 1, "Carbohydrates": 1, "DaysFresh": 1,
                                              "HungerChange": 1, "Lipids": 1, "Proteins": 1}
        assert m["script_item_blocks"] == 2
        assert m["script_modules"] == ["Base"]
        assert m["stats"]["script_files"] == 1
        assert "food_nutrition" not in m["signals"], "the lua sweep must not see script keys"
        assert mod_inventory.classify(m) == "content(scripts-only)"


def test_lua_nutrition_signal_still_fires_and_is_counted_separately():
    """The two sweeps are independent; only LongTermPreservation4220 shows both on the corpus."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "L", {"42/mod.info": "id=L\n",
                            "42/media/lua/client/a.lua": "local n = item:getNutrition()\n"})
        m = mod_inventory.scan_mod(mod)
        assert m["signals"]["food_nutrition"] == 1
        assert "script_nutrition" not in m["signals"]
        assert m["script_nutrition_keys"] == {} and m["script_item_blocks"] == 0
        assert m["script_modules"] == []


def test_item_lines_outside_an_item_block_are_counted_too():
    """`script_item_blocks` is an UPPER bound: a craftRecipe's inputs read `item 1 [Base.Bowl]`
    at line start and the regex cannot tell them from a definition. LongTermPreservation4220's
    47 = 17 real items + 30 recipe input lines. Documented in data/README.md, not papered over."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "R", {"42/mod.info": "id=R\n",
                            "42/media/scripts/items/x.txt": ITEM_SCRIPT,
                            "42/media/scripts/recipes/r.txt":
                                "craftRecipe Dry\n{\n  inputs\n  {\n    item 1 [Base.Apple]\n"
                                "    item 1 [Base.Bowl]\n  }\n  outputs\n  {\n"
                                "    item 1 Base.DriedApple\n  }\n}\n"})
        m = mod_inventory.scan_mod(mod)
        assert m["script_item_blocks"] == 5
        assert m["signals"]["script_nutrition"] == 6, "no nutrition key in the recipe file"


def test_size_and_mtime_cover_the_whole_folder_and_the_workshop_item():
    """`bytes` is every version folder, not the live one -- that is what a subscriber
    downloads. `workshop_item_mtime` reads the ITEM folder, one level above the mod."""
    with tempfile.TemporaryDirectory() as d:
        item = os.path.join(d, "123456")
        mod = _mod(d, "123456/mods/M", {"42/mod.info": "id=M\n",
                                        "42/media/lua/shared/x.lua": "a" * 100,
                                        "42.0/media/lua/shared/old.lua": "b" * 50})
        m = mod_inventory.scan_mod(mod, item)
        # 100 + 50 covers both version folders; mod.info is sized off disk because text-mode
        # writes on Windows turn its "\n" into two bytes.
        assert m["bytes"] == 100 + 50 + os.path.getsize(os.path.join(mod, "42", "mod.info"))
        assert m["lua_kb"] == 0 and m["stats"] == {"lua_shared": 1}
        assert m["workshop_item_mtime"] == datetime.datetime.fromtimestamp(
            os.path.getmtime(item)).isoformat(timespec="seconds")


def test_resolve_returns_the_live_folder_the_walk_uses():
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "X", {"42.13/mod.info": "id=X\n", "media/lua/shared/b41.lua": "print(1)\n"})
        info, vers, chosen, live = mod_inventory.resolve(mod)
        assert info == {"id": "X"} and vers == ["42.13"] and chosen == "42.13/mod.info"
        assert live == os.path.join(mod, "42.13")
        # The b41-flat copy at the root is NOT what B42 loads, so it is not this mod's content.
        assert mod_inventory.scan_mod(mod)["stats"] == {}


WORKSHOP = mod_inventory.ROOT
LTP = os.path.join(WORKSHOP, "3774789651", "mods", "LongTermPreservation4220")
SRJ = os.path.join(WORKSHOP, "3782784855", "mods", "Skill Recovery Journal")
DATASET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data",
                       "mod-inventory.json")


@unittest.skipUnless(os.path.isdir(LTP), "LongTermPreservation4220 not installed at %s" % LTP)
def test_installed_long_term_preservation_declares_a_different_id():
    """Slice 08's top nutrition candidate, and the row that proves both halves of this change:
    the folder says LongTermPreservation4220, the mod.info says SKITTLE_..., and its nutrition
    is entirely in scripts (135 key hits) with a 4-hit lua tail. Measured 2026-09-10."""
    m = mod_inventory.scan_mod(LTP)
    assert m["mod_id"] == "SKITTLE_LongTermPreservation4220"
    assert m["mod_id_fallback"] == "LongTermPreservation4220"
    assert m["signals"]["script_nutrition"] == 135
    assert m["signals"]["food_nutrition"] == 4
    assert m["script_modules"] == ["Skittles"], "adds items, overrides no vanilla one"


@unittest.skipUnless(os.path.isdir(SRJ), "Skill Recovery Journal 3782784855 not installed")
def test_installed_skill_recovery_journal_has_no_resolvable_id():
    assert mod_inventory.scan_mod(SRJ)["mod_id"] == ""


@unittest.skipUnless(os.path.isfile(DATASET), "data/mod-inventory.json not generated")
def test_committed_dataset_carries_resolved_ids_and_the_new_fields():
    """The dataset slices 09-11 pick teardown targets from. Every row a profile could name
    must carry the id the game resolves, or an explicit empty one."""
    rows = json.load(open(DATASET, encoding="utf-8"))
    assert len(rows) == 230, "230 mod folders at 2026-09-10 15:30"
    assert len({r["workshop_id"] for r in rows}) == 179
    assert sum(1 for r in rows if not r["mod_id"]) == 1
    assert all(set(r) >= {"mod_id", "mod_id_fallback", "version_dirs", "mod_info_at",
                          "script_nutrition_keys", "script_item_blocks", "script_modules",
                          "bytes", "workshop_item_mtime"} for r in rows)
    assert [r["mod_id"] for r in rows if r["folder"] == "LongTermPreservation4220"] == \
        ["SKITTLE_LongTermPreservation4220"]
    assert sum(1 for r in rows if r["signals"].get("script_nutrition")) == 9
    assert sum(1 for r in rows if r["signals"].get("food_nutrition")) == 11


@unittest.skipUnless(os.path.isdir(LTP), "LongTermPreservation4220 not installed at %s" % LTP)
def test_a_rescan_of_the_same_folder_is_byte_identical():
    """Committed data has to be reproducible: same tree in, same bytes out. Only the
    workshop mtime could drift, and it is read, never taken from the clock."""
    one, two = mod_inventory.scan_mod(LTP), mod_inventory.scan_mod(LTP)
    assert json.dumps(one, sort_keys=True) == json.dumps(two, sort_keys=True)
