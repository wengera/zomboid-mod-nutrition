"""Tests for the L0 mod layout lint.

The synthetic fixtures are the shapes the installed 230-mod corpus actually ships (each test
names the mods it stands in for); the `skipUnless` block at the bottom pins the three real
folders whose findings the slice-07 plan is written against.
"""
import os, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import mod_lint

CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mod_lint.py")


def _write(d, rel, text):
    p = os.path.join(d, *rel.split("/")); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(text); return p


def _mod(d, name, files):
    """Build the mod folder `d/name` from {relative path: contents} and return it."""
    for rel, text in files.items():
        _write(d, name + "/" + rel, text)
    return os.path.join(d, *name.split("/"))


def _run(*args):
    return subprocess.run([sys.executable, CLI] + list(args), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def test_good_layout_lints_clean():
    """The B42 shape every rule is written against: one version folder holding mod.info+media,
    folder named after the id."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "Good", {"42/mod.info": "name=Good Mod\nid=Good\n",
                               "42/media/lua/shared/x.lua": "print('hi')\n"})
        assert mod_lint.lint([mod]) == []
        r = _run(mod)
        assert r.stdout.strip() == "0 finding(s): 0 ERROR, 0 WARN, 0 INFO across 1 mod(s)", r.stdout
        assert r.returncode == 0


def test_bad_layout_flags_exactly_version_dir_and_loadstring():
    """No version folder, mod.info at the root, a loadstring call. Exactly two ERRORs: with no
    version folder there is no version folder for mod.info to be missing from (mod-info-place
    would just restate version-dir), and root `media/` is that same b41-flat fact again."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "bad", {"mod.info": "name=bad\nid=bad\n",
                              "media/lua/shared/x.lua": 'loadstring("return 1")\n'})
        findings = mod_lint.lint([mod])
        assert {f.rule for f in findings} == {"version-dir", "loadstring"}
        assert {f.level for f in findings} == {"ERROR"}
        r = _run(mod)
        assert ": ERROR: loadstring: media/lua/shared/x.lua:1" in r.stdout, r.stdout
        assert r.stdout.strip().endswith("2 finding(s): 2 ERROR, 0 WARN, 0 INFO across 1 mod(s)"), r.stdout
        assert r.returncode == 1


def test_mod_info_in_common_only_warns_and_still_passes():
    """AutoCook/gasmask/WorkingKnowledge's shape: the id resolves out of `common/`, not out of
    the folder the running build reads. Worth knowing, not worth failing a run over."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "Common", {"common/mod.info": "id=Common\n",
                                 "42/media/lua/shared/x.lua": "print(1)\n"})
        findings = mod_lint.lint([mod])
        assert [(f.level, f.rule) for f in findings] == [("WARN", "mod-info-place")]
        assert findings[0].detail.startswith("mod.info is common/mod.info, not 42/mod.info")
        assert _run(mod).returncode == 0


def test_mod_info_in_an_older_version_dir_warns():
    """MoodleFramework 3396446795: mod.info in 42.0/ while the live folder is 42.20/. The id it
    resolves to is whatever that older file says, so the placement rule reads 'newest', not 'any'."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "MF", {"42.0/mod.info": "id=MF\n", "42.20/media/lua/shared/x.lua": "print(1)\n"})
        findings = mod_lint.lint([mod])
        assert [(f.level, f.rule) for f in findings] == [("WARN", "mod-info-place")]
        assert "42.0/mod.info, not 42.20/mod.info" in findings[0].detail


def test_disagreeing_ids_across_version_dirs():
    """SD_CC_TEST 3774052732's shape: two mod.info files, two ids. A profile naming either one
    resolves to a different folder depending on which file the reader happens to open."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "B", {"42/mod.info": "id=A\n", "42.20/mod.info": "id=B\n",
                            "42.20/media/lua/shared/x.lua": "print(1)\n"})
        findings = mod_lint.lint([mod])
        assert [(f.level, f.rule) for f in findings] == [("ERROR", "id-agree")]
        assert "42/mod.info (A)" in findings[0].detail and "42.20/mod.info (B)" in findings[0].detail


def test_missing_mod_info_fails_mod_info_and_id_only():
    """Skill Recovery Journal 3782784855 ships only `42.20.1/media`. Two ERRORs -- and no
    mod-info-place WARN: the missing file is already reported, once, at the level that matters."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "NoInfo", {"42.20.1/media/lua/shared/x.lua": "print(1)\n"})
        assert {f.rule for f in mod_lint.lint([mod])} == {"mod-info", "id"}


def test_empty_id_is_an_error_and_suppresses_the_folder_comparison():
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "E", {"42/mod.info": "name=E\nid=\n", "42/media/scripts/x.txt": ""})
        assert [(f.level, f.rule) for f in mod_lint.lint([mod])] == [("ERROR", "id")]


def test_media_only_in_common_warns_and_names_where_it_is():
    """25 of the 230 installed folders ship `common/media` with an empty version folder. The
    WARN has to say where the content really is, or copying the version folder alone looks fine."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "C", {"42/mod.info": "id=C\n", "common/media/lua/shared/x.lua": "print(1)\n"})
        findings = mod_lint.lint([mod])
        assert [(f.level, f.rule) for f in findings] == [("WARN", "media")]
        assert findings[0].detail == "no 42/media (media/ at: common/media)"


def test_folder_name_mismatch_is_informational_only():
    """51 installed folders differ from their id; `mods.install` keeps the folder name on
    purpose, so this can never fail a run."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "Some Folder", {"42/mod.info": "id=RealId\n", "42/media/lua/shared/x.lua": ""})
        findings = mod_lint.lint([mod])
        assert [(f.level, f.rule) for f in findings] == [("INFO", "folder-id")]
        assert findings[0].detail == "folder 'Some Folder' != id 'RealId'"
        assert _run(mod).returncode == 0


def test_loadstring_reports_the_first_line_and_counts_the_rest():
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "L", {"42/mod.info": "id=L\n",
                            "42/media/lua/client/a.lua": "-- ok\nlocal f = loadstring(s)\nloadstring (t)\n"})
        findings = [f for f in mod_lint.lint([mod]) if f.rule == "loadstring"]
        assert len(findings) == 1
        assert findings[0].detail.startswith("42/media/lua/client/a.lua:2 and 1 more")


def test_lua_outside_media_is_still_scanned():
    """The rule is 'no loadstring in any .lua under the folder' -- a mod that hides one in a
    stray folder still breaks on 42.20.x."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "S", {"42/mod.info": "id=S\n", "42/media/lua/shared/x.lua": "print(1)\n",
                            "extra/tools/gen.lua": "loadstring('x')\n"})
        assert [f.rule for f in mod_lint.lint([mod])] == ["loadstring"]


def test_version_dirs_sort_by_parsed_tuple_not_by_string():
    """A string sort puts '42.9' above '42.20'; three-part names ('42.20.1') are real."""
    with tempfile.TemporaryDirectory() as d:
        mod = _mod(d, "V", {n + "/keep": "" for n in
                            ("42", "42.9", "42.20", "42.20.1", "41", "42.x", "common", "media")})
        assert mod_lint.version_dirs(mod) == ["42.20.1", "42.20", "42.9", "42"]


def test_read_info_lowercases_keys_last_wins_and_survives_a_bom():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "mod.info")
        open(p, "wb").write(b"\xef\xbb\xbfID=First\nname = Mod\nid=Second\nnot a pair\n")
        assert mod_lint.read_info(p) == {"id": "Second", "name": "Mod"}


def test_workshop_id_target_expands_to_every_mod_the_item_ships():
    with tempfile.TemporaryDirectory() as d:
        a = _mod(d, "123456/mods/A", {"42/mod.info": "id=A\n", "42/media/lua/shared/x.lua": ""})
        b = _mod(d, "123456/mods/B", {"42/mod.info": "id=B\n", "42/media/lua/shared/x.lua": ""})
        assert mod_lint.mod_dirs(["123456"], d) == [a, b]
        assert mod_lint.display_name(a, d) == "123456/A"
        assert mod_lint.lint(["123456"], d) == []
        r = _run("--workshop-dir", d, "123456")
        assert r.stdout.strip().endswith("across 2 mod(s)"), r.stdout


def test_no_targets_sweeps_the_whole_workshop_root():
    with tempfile.TemporaryDirectory() as d:
        _mod(d, "111/mods/A", {"42/mod.info": "id=A\n", "42/media/lua/shared/x.lua": ""})
        _mod(d, "222/mods/B", {"media/lua/shared/x.lua": ""})
        findings = mod_lint.lint([], d)
        assert [(f.path, f.rule) for f in findings] == [("222/B", "version-dir"), ("222/B", "mod-info"),
                                                        ("222/B", "id")]
        r = _run("--workshop-dir", d)
        assert r.stdout.strip().endswith("3 finding(s): 3 ERROR, 0 WARN, 0 INFO across 2 mod(s)"), r.stdout
        assert r.returncode == 1


def test_unknown_targets_exit_with_a_message_not_a_traceback():
    for target, expected in [("no-such-folder", "no such mod folder"), ("999999", "no mods/ folder")]:
        try:
            mod_lint.mod_dirs([target])
            assert False, "expected SystemExit for %r" % target
        except SystemExit as e:
            assert expected in str(e), e
    r = _run("no-such-folder")
    assert "Traceback" not in r.stderr, r.stderr


WORKSHOP = mod_lint.WORKSHOP_DIR
KEEN = os.path.join(WORKSHOP, "3685392864", "mods", "KeenPerception")
SRJ = os.path.join(WORKSHOP, "3782784855", "mods", "Skill Recovery Journal")
SD_CC = os.path.join(WORKSHOP, "3774052732", "mods", "SD_CC_TEST")


@unittest.skipUnless(os.path.isdir(KEEN), "KeenPerception not installed at %s" % KEEN)
def test_installed_keen_perception_is_clean():
    """Slice 07's two-mod profile rides on this one; it has to lint clean by workshop id."""
    assert mod_lint.lint(["3685392864"]) == []
    r = _run("3685392864")
    assert r.stdout.strip() == "0 finding(s): 0 ERROR, 0 WARN, 0 INFO across 1 mod(s)", r.stdout
    assert r.returncode == 0


@unittest.skipUnless(os.path.isdir(SRJ), "Skill Recovery Journal 3782784855 not installed")
def test_installed_skill_recovery_journal_has_no_mod_info():
    """The one corpus folder `mods.workshop_index()` cannot see (229 ids for 230 folders)."""
    assert {f.rule for f in mod_lint.lint([SRJ])} == {"mod-info", "id"}


@unittest.skipUnless(os.path.isdir(SD_CC), "SD_CC_TEST 3774052732 not installed")
def test_installed_sd_cc_test_declares_two_ids():
    """`sd_cc_test` in 42/ and the root, `SD_CC_TEST_42` in common/ -- the corpus's only
    id-agree failure, and the reason the rule exists."""
    findings = [f for f in mod_lint.lint([SD_CC]) if f.rule == "id-agree"]
    assert len(findings) == 1 and "SD_CC_TEST_42" in findings[0].detail
