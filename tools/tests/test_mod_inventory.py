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
        # With no version folder, `common/` IS the live folder, so its media is counted.
        assert m["live_media"] is True and m["media_at"] == ["common/media"]


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


def test_item_definitions_are_counted_exactly_and_recipe_lines_are_not():
    """`script_item_blocks` counts item DEFINITIONS, exactly -- it is not an upper bound.

    A craftRecipe writes its inputs and outputs as `item 1 [Base.Bowl]` at line start, which the
    first regex (`^\\s*item\\s+(\\S+)`) could not tell from a definition: LongTermPreservation4220
    read 47 there (17 real items + 30 recipe lines) and reads 17 now. Anchoring the name to the
    end of the line is what separates them, and it must not cost the `item Name {` style.

    The name class must also hold a **hyphen**. `3470426196/KATTAJ1 Military Pack` writes
    `item Military_ArmsProtectionLower_Patriot_Light-Black` with the brace on the next line;
    `\\w[\\w.]*` stopped at the `-`, leaving `Black` on the line and the whole definition
    unmatched, so the row read 1 for 492 items (2026-09-10). `-` is the only character beyond
    `[\\w.]` any id in the corpus uses."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "R", {"42/mod.info": "id=R\n",
                            "42/media/scripts/items/x.txt": ITEM_SCRIPT,
                            "42/media/scripts/items/brace.txt":
                                "module Base\n{\n\titem OnTheSameLine {\n"
                                "\t\tDisplayName = On The Same Line,\n\t}\n}\n",
                            # KATTAJ1's shape, both brace styles.
                            "42/media/scripts/items/hyphen.txt":
                                "module KATTAJ1\n{\n"
                                "\titem Military_ArmsProtectionLower_Patriot_Light-Black\n"
                                "\t{\n\t\tDisplayName = Patriot Light Black,\n\t}\n"
                                "\titem Military_Vest_Ranger-Desert {\n"
                                "\t\tDisplayName = Ranger Desert,\n\t}\n}\n",
                            "42/media/scripts/recipes/r.txt":
                                "craftRecipe Dry\n{\n  inputs\n  {\n    item 1 [Base.Apple]\n"
                                "    item 1 [Base.Bowl]\n  }\n  outputs\n  {\n"
                                "    item 1 Base.DriedApple\n  }\n}\n"})
        m = mod_inventory.scan_mod(mod)
        assert m["script_item_blocks"] == 5, \
            ("DriedApple + DriedPear + OnTheSameLine + both hyphenated ids; "
             "not one of the 3 recipe `item` lines")
        assert m["signals"]["script_nutrition"] == 6, "no nutrition key in the recipe file"
        assert m["script_modules"] == ["Base", "KATTAJ1"]


def test_a_commented_out_definition_is_not_a_definition():
    """The engine ignores `/* ... */` and `//`, and so does `food_scan.parse_script`; this scan
    did not, so it counted item blocks and nutrition keys the build never loads.

    `SKITTLE_LongTermPreservation4220`'s shape, both halves of it: a whole `/* OBSOLETE */`
    block holding two complete definitions (`items_dried.txt:374-409`, 36 lines, `DriedPork`
    and `DriedBeef`) and a two-line `/*DaysFresh = …,\\nDaysTotallyRotten = …,*/` inside a live
    item (`:180-181` and three more). Only the SECOND line of that pair was ever counted --
    `SCRIPT_KEYS` anchors to line start and the first line begins with `/*` -- which is why the
    four two-liners cost 4 keys, not 8. `//` is stripped too, for the same reason `parse_script`
    strips it; exactly one script file in the 230-mod corpus contains the token and no count in
    it moves (2026-09-10)."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "LTP", {"42.20/mod.info": "id=SKITTLE_LTP\n",
                              "42.20/media/scripts/items/x.txt": ITEM_SCRIPT +
                              "module Skittles\n{\n"
                              "\titem Live\n\t{\n\t\tCalories = 100,\n"
                              "\t\t/*DaysFresh = 60,\n\t\tDaysTotallyRotten = 90,*/\n\t}\n"
                              "/* OBSOLETE\n\titem DriedPork\n\t{\n\t\tCalories = 200,\n"
                              "\t\tProteins = 20,\n\t}\n\titem DriedBeef\n\t{\n"
                              "\t\tCalories = 300,\n\t}\n*/\n"
                              "\t// item CommentedOutWithSlashes\n}\n"})
        m = mod_inventory.scan_mod(mod)
        assert m["script_item_blocks"] == 3, "DriedApple + DriedPear + Live; nothing commented"
        assert m["script_nutrition_keys"] == {"Calories": 2, "Carbohydrates": 1, "DaysFresh": 1,
                                              "HungerChange": 1, "Lipids": 1, "Proteins": 1}, \
            "the live Calories, and not one key from inside a comment"
        assert m["script_modules"] == ["Base", "Skittles"]


def test_sandbox_options_are_seen_in_common_media_too():
    """`sandbox_options` read `<live>/media` and `<mod>/media` only, so it was false on 11 of
    the 55 corpus mods that ship `sandbox-options.txt` **only** in `common/media`
    (`3398090604`, `3404074048`, `3645980077`, four mods in `3662913642`, `3671176591`,
    `3763759011`, `3772533498`, `3789019583`, 2026-09-10). `common/media` is a layout the build
    also loads, a profile reads sandbox options off this field, and a false "no options" is the
    dangerous direction -- so all three roots are checked."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "SD", {"42/mod.info": "id=SD\n",
                             "42/media/lua/shared/x.lua": "print(1)\n",
                             "common/media/sandbox-options.txt": "VERSION = 1,\n"})
        m = mod_inventory.scan_mod(mod)
        assert m["sandbox_options"] is True
        assert m["layout"] == "42" and "common/media" in m["media_at"]
        # ...and the field still says false when no root has one.
        bare = _mod(d, "NB", {"42/mod.info": "id=NB\n", "42/media/lua/shared/x.lua": "print(1)\n"})
        assert mod_inventory.scan_mod(bare)["sandbox_options"] is False


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


def test_no_workshop_item_folder_means_no_workshop_stamp():
    """With no item folder there is no Steam stamp to read, and the field is `None`. The mod
    folder's own mtime answers a different question -- Steam rewrites a mod folder without
    touching the item folder above it (`3490370700`, 2026-09-10) -- so it must not stand in."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "M", {"42/mod.info": "id=M\n", "42/media/lua/shared/x.lua": "print(1)\n"})
        assert mod_inventory.scan_mod(mod)["workshop_item_mtime"] is None
        assert mod_inventory.scan_mod(mod, os.path.dirname(mod))["workshop_item_mtime"] is not None


def test_resolve_returns_the_media_root_and_the_live_folder_the_walk_uses():
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "X", {"42.13/mod.info": "id=X\n", "media/lua/shared/b41.lua": "print(1)\n"})
        info, vers, chosen, root, live = mod_inventory.resolve(mod)
        assert info == {"id": "X"} and vers == ["42.13"] and chosen == "42.13/mod.info"
        assert root == "42.13" and live == os.path.join(mod, "42.13")
        # The b41-flat copy at the root is NOT what B42 loads, so it is not this mod's content.
        m = mod_inventory.scan_mod(mod)
        assert m["stats"] == {}
        assert m["layout"] == root, "`layout` is the media root, not a second reading of it"
        # ...and the zero is legible rather than mute: nothing under the live folder, one
        # `media/` elsewhere in the mod.
        assert m["live_media"] is False and m["media_at"] == ["media"]


def test_a_mod_with_neither_a_version_folder_nor_common_is_flat_b41():
    """The third `layout` branch, the one `media_root` reports as `""`: no `42*/`, no
    `common/`, the b41 layout with everything at the root. `mod_lint`'s `version-dir` ERROR
    fires on it and the content is still read, because a flat mod does load for some mods
    (`docs/modding/README.md:22`). No installed corpus row is in this branch today."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "Flat", {"mod.info": "id=Flat\nname=Flat\n",
                               "media/lua/shared/a.lua": "print(1)\n",
                               "media/scripts/items/x.txt": ITEM_SCRIPT})
        info, vers, chosen, root, live = mod_inventory.resolve(mod)
        assert vers == [] and chosen == "mod.info" and root == "" and live == mod
        m = mod_inventory.scan_mod(mod)
        assert m["layout"] == "flat(b41?)" and m["version_dirs"] == []
        assert m["live_media"] is True and m["media_at"] == ["media"]
        assert m["stats"] == {"lua_shared": 1, "script_files": 1}


def test_content_in_common_media_reads_as_zero_and_the_record_says_why():
    """`3520263838/EN_Newburbs`' shape: a version folder decides the layout, every file lives
    in `common/media`, and `common/media` is a layout the running build ALSO loads. This scan
    counts `<live>/media` alone -- the de-duplication the record needs -- so the row reads
    empty, and `live_media` + `media_at` are how a consumer tells that from a mod that ships
    nothing at all. 24 of the 230 installed rows, 2026-09-10. No merge rule is asserted."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "EN", {"42/mod.info": "id=EN\n",
                             "common/media/scripts/items/x.txt": ITEM_SCRIPT})
        m = mod_inventory.scan_mod(mod)
        assert m["layout"] == "42" and m["stats"] == {} and m["signals"] == {}
        assert m["script_item_blocks"] == 0 and m["script_nutrition_keys"] == {}
        assert m["live_media"] is False, "the 42/ folder holds no media/"
        assert m["media_at"] == ["common/media"], "...but the mod does ship one"
        assert mod_inventory.classify(m) == "other"


def test_a_declared_but_empty_name_or_author_is_undeclared():
    """`name=` with nothing after it says no more than a missing `name=` line, and both read
    `?` -- the collapse `mod_id` already made for an empty `id=`."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "E", {"42/mod.info": "id=E\nname=\nauthor=   \n"})
        m = mod_inventory.scan_mod(mod)
        assert m["mod_id"] == "E"
        assert m["name"] == "?" and m["author"] == "?"


WORKSHOP = mod_inventory.ROOT
LTP = os.path.join(WORKSHOP, "3774789651", "mods", "LongTermPreservation4220")
SRJ = os.path.join(WORKSHOP, "3782784855", "mods", "Skill Recovery Journal")
DATASET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data",
                       "mod-inventory.json")


@unittest.skipUnless(os.path.isdir(LTP), "LongTermPreservation4220 not installed at %s" % LTP)
def test_installed_long_term_preservation_declares_a_different_id():
    """Slice 08's top nutrition candidate, and the row that proves both halves of this change:
    the folder says LongTermPreservation4220, the mod.info says SKITTLE_..., and its nutrition
    is entirely in scripts (117 key hits) with a 4-hit lua tail. Measured 2026-09-10 17:47."""
    m = mod_inventory.scan_mod(LTP)
    assert m["mod_id"] == "SKITTLE_LongTermPreservation4220"
    assert m["mod_id_fallback"] == "LongTermPreservation4220"
    assert m["signals"]["script_nutrition"] == 117
    assert m["signals"]["food_nutrition"] == 4
    assert m["script_modules"] == ["Skittles"], "adds items, overrides no vanilla one"
    # The exact-count fix, on the real folder the catalog quotes: 15 definitions. The 30
    # craftRecipe input lines that used to inflate this to 47 are gone, and so are the two
    # inside `items_dried.txt`'s `/* OBSOLETE */` block, which took it from 17 to 15.
    assert m["script_item_blocks"] == 15
    # 135 -> 117 is 14 (the two commented definitions, 7 keys each) + 4 (one DaysTotallyRotten
    # in each of the four two-line comment blocks; their DaysFresh line never matched).
    assert m["script_nutrition_keys"] == {"Calories": 14, "Carbohydrates": 14, "DaysFresh": 14,
                                          "DaysTotallyRotten": 14, "EvolvedRecipe": 5,
                                          "FoodType": 9, "HungerChange": 14, "Lipids": 14,
                                          "Proteins": 14, "ThirstChange": 5}


@unittest.skipUnless(os.path.isdir(SRJ), "Skill Recovery Journal 3782784855 not installed")
def test_installed_skill_recovery_journal_has_no_resolvable_id():
    assert mod_inventory.scan_mod(SRJ)["mod_id"] == ""


@unittest.skipUnless(os.path.isfile(DATASET), "data/mod-inventory.json not generated")
def test_committed_dataset_carries_resolved_ids_and_the_new_fields():
    """The dataset slices 09-11 pick teardown targets from. Every row a profile could name
    must carry the id the game resolves, or an explicit empty one."""
    rows = json.load(open(DATASET, encoding="utf-8"))
    assert len(rows) == 230, "230 mod folders at 2026-09-10 17:47"
    assert len({r["workshop_id"] for r in rows}) == 179
    assert sum(1 for r in rows if not r["mod_id"]) == 1
    assert all(set(r) >= {"mod_id", "mod_id_fallback", "version_dirs", "mod_info_at",
                          "live_media", "media_at", "script_nutrition_keys",
                          "script_item_blocks", "script_modules", "bytes",
                          "workshop_item_mtime"} for r in rows)
    assert [r["mod_id"] for r in rows if r["folder"] == "LongTermPreservation4220"] == \
        ["SKITTLE_LongTermPreservation4220"]
    assert sum(1 for r in rows if r["signals"].get("script_nutrition")) == 9
    assert sum(1 for r in rows if r["signals"].get("food_nutrition")) == 11
    assert [r["script_item_blocks"] for r in rows
            if r["folder"] == "LongTermPreservation4220"] == [15]
    # The hyphen fix on the one row it moved: `-` in an item id used to end the match, so this
    # row recorded 1 of its 492 definitions (2026-09-10). It ships no comment block, so the
    # comment-stripping fix leaves it where it was.
    assert [r["script_item_blocks"] for r in rows
            if r["folder"] == "KATTAJ1 Military Pack"] == [492]
    # The comment fix moved exactly two rows: LTP 17 -> 15 and ZVirusVaccine42BETA 102 -> 86
    # (`LabItemsOld.txt` 12 -> 0 and `LabTestZone.txt` 2 -> 0, each one whole-file block
    # comment, plus 2 in `LabItems.txt`). Over the nine `script_nutrition` mods: 899 -> 881.
    assert [r["script_item_blocks"] for r in rows
            if r["folder"] == "ZVirusVaccine42BETA"] == [86]
    assert sum(r["script_item_blocks"] for r in rows
               if r["signals"].get("script_nutrition")) == 881
    # Corpus total pinned so a Steam rewrite cannot rot the sum silently (2026-09-10 17:47).
    assert sum(r["script_item_blocks"] for r in rows) == 6630
    # `sandbox_options` reads `common/media` too, which is where 11 of these 55 keep the file.
    assert sum(1 for r in rows if r["sandbox_options"]) == 55


@unittest.skipUnless(os.path.isfile(DATASET), "data/mod-inventory.json not generated")
def test_committed_dataset_pins_the_rows_whose_content_is_not_under_the_live_folder():
    """A zero in this dataset has two causes and they must not be confused. 24 rows have no
    `<live>/media` at all (`live_media` false) -- every one of them keeps its files in
    `common/media`, which the running build loads and this scan does not count. 7 more DO have
    a live `media/`, holding only file kinds `stats` has no bucket for: 182 `.json` (map
    definitions and `lua/shared/Translate/**` strings), 21 `.txt` (more translations, plus
    empty-folder placeholders), 4 `.frag` shaders and 1 `.xml` -- and **no** `.png`/`.dds`/
    `.tga` at all, so "textures" is the wrong word for them. Together that is the 31
    empty-`stats` rows, all of which classify as `other`.

    `live_media` is not the general guard, though: 177 rows have a `common/media` this scan did
    not read and only 24 of them are blank, so `media_at` is what says whether a zero is
    trustworthy. Measured 2026-09-10; re-measure with the dataset, the workshop tree is live."""
    rows = json.load(open(DATASET, encoding="utf-8"))
    dark = [r for r in rows if not r["live_media"]]
    assert len(dark) == 24
    assert all("common/media" in r["media_at"] for r in dark), \
        "every one of them ships common/media -- the content is there, not missing"
    assert all(not r["stats"] and not r["signals"] for r in dark)
    empty = [r for r in rows if not r["stats"]]
    assert len(empty) == 31 and all(r["class"] == "other" for r in empty)
    assert sum(1 for r in empty if r["live_media"]) == 7
    assert sum(1 for r in rows if "common/media" in r["media_at"]) == 177, \
        "the uncounted-content set is 177 rows, not the 24 with no live media/ at all"


@unittest.skipUnless(os.path.isdir(LTP), "LongTermPreservation4220 not installed at %s" % LTP)
def test_a_rescan_of_the_same_folder_is_byte_identical():
    """Committed data has to be reproducible: same tree in, same bytes out. Nothing here is
    taken from the clock -- the one time value is the workshop item's mtime, read off disk (and
    `None` here, since no item folder is passed)."""
    one, two = mod_inventory.scan_mod(LTP), mod_inventory.scan_mod(LTP)
    assert json.dumps(one, sort_keys=True) == json.dumps(two, sort_keys=True)
