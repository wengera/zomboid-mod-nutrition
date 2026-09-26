import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import claims_check as cc
import claimslib as cl

CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "claims_check.py")


def _write(d, rel, text):
    p = os.path.join(d, *rel.split("/")); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8", newline="\n").write(text); return p


def _row(i, **kw):
    r = {"id": cl.id_str(i), "claim": "claim %d with 42 in it" % i, "grade": "C", "pointer": "jar:Nutrition.update @0 L65",
         "bound": "", "status": "settled", "successor": "", "kind": "mechanism",
         "source": "docs/vanilla/nutrition-core.md § X", "owner": "facts/nutrition-core.md#update"}
    r.update(kw); return r


def _tree(d, rows, pages=None, skills=None, dnc="run,key,value,why,read_instead\n", aliases="alias,run,file,key\n"):
    cl.write_register(_write(d, "docs/reference/claims.tsv", ""), rows)
    _write(d, "docs/reference/do-not-cite.csv", dnc); _write(d, "docs/reference/run-aliases.csv", aliases)
    for rel, text in (pages or {}).items():
        _write(d, rel, text)
    for rel, text in (skills or {}).items():
        _write(d, rel, text)
    return d


def _rules(findings):
    return sorted({f.rule for f in findings})


def test_schema_gap_duplicate_and_successor():
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1), _row(3), _row(3, claim="dup"), _row(4, status="superseded", successor="#0099")])
        f = cc.check(d, register_only=True)
        details = " | ".join(x.detail for x in f)
        assert "gap" in details and "duplicate" in details and "#0099" in details and _rules(f) == ["schema"]


def test_pointer_rule_runs_aliases_and_do_not_cite():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "testing", "artifacts", "x123-20260911-034426"))
        open(os.path.join(d, "testing", "artifacts", "x123-20260911-034426", "platform-folder.json"), "w").write("{}")
        rows = [_row(1, grade="M", pointer="run:x123b-20260911-034500 platform-folder.json boots.common_id"),
                _row(2, grade="M", pointer="run:nope-20260101-000000 a.json k"),
                _row(3, grade="M", pointer="run:x123-20260911-034426 platform-folder.json summary.bad"),
                _row(4, pointer='repo:tools/missing.py:3 "x"'), _row(5, pointer="repo:tools/x.py:3")]
        _write(d, "tools/x.py", "x = 1\n")
        _tree(d, rows, dnc="run,key,value,why,read_instead\nx123-20260911-034426,summary.bad,1,wrong,\n",
              aliases="alias,run,file,key\nx123b-20260911-034500,x123-20260911-034426,platform-folder.json,boots.common_id\n")
        f = cc.check(d, register_only=True)
        assert "#0001" not in [x.detail[:5] for x in f]
        assert any("nope-20260101-000000" in x.detail for x in f)          # missing run folder
        assert any("do-not-cite" in x.detail and "#0003" in x.detail for x in f)
        assert any("missing.py" in x.detail for x in f)                   # repo path missing
        assert any("anchor" in x.detail and "#0005" in x.detail for x in f)


# The two child-key tests below share one tree: run x121 with `phases.M7` restricted and a `*`
# whole-run prose row beside it (Ruling R34).
_DNC_CHILD = ("run,key,value,why,read_instead\n"
              "x121-20260911-030023,phases.M7,1,the gate straddles the window,\n"
              "x121-20260911-030023,*,,the client console prints each block twice,\n")


def _child_tree(d, rows):
    os.makedirs(os.path.join(d, "testing", "artifacts", "x121-20260911-030023"))
    open(os.path.join(d, "testing", "artifacts", "x121-20260911-030023", "x121.json"), "w").write("{}")
    return _tree(d, rows, dnc=_DNC_CHILD)


def test_do_not_cite_flags_a_child_of_a_restricted_key():
    """R34: `phases.M7` is listed, so `phases.M7.before` — a reading inside it — is uncitable."""
    with tempfile.TemporaryDirectory() as d:
        _child_tree(d, [_row(1, grade="M", pointer="run:x121-20260911-030023 x121.json phases.M7.before"),
                        _row(2, grade="M", pointer="run:x121-20260911-030023 x121.json phases.M7[0].after"),
                        _row(3, grade="M", pointer="run:x121-20260911-030023 x121.json phases.M7")])
        f = cc.check(d, register_only=True)
        for cid in ("#0001", "#0002", "#0003"):
            assert any("do-not-cite" in x.detail and cid in x.detail for x in f), cid
        assert any("child of the restricted key phases.M7" in x.detail and "#0001" in x.detail for x in f)


def test_do_not_cite_leaves_a_sibling_and_an_ancestor_alone():
    """A sibling (`phases.M8`) and the ancestor (`phases`) of a restricted key still pass, and a
    `*` whole-run row fails nothing on its own — it is discharged in the row's bound."""
    with tempfile.TemporaryDirectory() as d:
        _child_tree(d, [_row(1, grade="M", pointer="run:x121-20260911-030023 x121.json phases.M8"),
                        _row(2, grade="M", pointer="run:x121-20260911-030023 x121.json phases.M70"),
                        _row(3, grade="M", pointer="run:x121-20260911-030023 x121.json phases")])
        f = cc.check(d, register_only=True)
        assert not [x for x in f if "do-not-cite" in x.detail], [x.detail for x in f]
        assert f == []


def test_owner_tag_suffix_provisional_and_fix():
    page = "# Core\nVerified against 42.20.4 (b0bbce05d5) · 2026-09-17 · scope: x\n\n## Key facts\n- Update runs each tick [#0001].\n- Burn is 0.016 [#0002].\n- Unknown [#0099].\n- Draft [T2.1].\n\n## How it works\n\nThe store clamps at 3700 [#0003/M].\n"
    with tempfile.TemporaryDirectory() as d:
        rows = [_row(1), _row(2, grade="M", pointer="run:r-20260101-000000 f.json k", bound="n=1"), _row(3, grade="M", pointer="run:r-20260101-000000 f.json k"),
                _row(4, owner="facts/missing.md#a")]
        os.makedirs(os.path.join(d, "testing", "artifacts", "r-20260101-000000"))
        _tree(d, rows, pages={"docs/facts/nutrition-core.md": page})
        f = cc.check(d)
        assert any(x.rule == "tag" and "#0002" in x.detail and "/M/n=1" in x.detail for x in f)   # suffix drift
        assert any(x.rule == "tag" and "#0099" in x.detail for x in f)
        assert any(x.rule == "tag" and "T2.1" in x.detail for x in f)
        assert any(x.rule == "owner" and "#0004" in x.detail for x in f)
        assert not any(x.rule == "owner" and "#0004" in x.detail for x in cc.check(d, partial=True))
        assert not any("T2.1" in x.detail for x in cc.check(d, allow_provisional=True))
        cc.fix_tags(d)
        text = open(os.path.join(d, "docs", "facts", "nutrition-core.md"), encoding="utf-8").read()
        assert "[#0002/M/n=1]" in text and "[#0001]" in text and "[#0003/M]" in text
        assert not any(x.rule == "tag" and "#0002" in x.detail for x in cc.check(d, partial=True, allow_provisional=True))


def test_untagged_numbers_warn_only_outside_fences_and_procedure():
    page = "# P\nVerified against 42.20.4 (b0bbce05d5)\n\n## Rules\n- Do it: because 3 things [#0001].\n\n## How it works\n\nThere are 12 keys.\n\n```lua\nlocal x = 12\n```\n\n## Procedure\n\n1. Run 3 times.\n"
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1, owner="platform/jar-research.md#rules")], pages={"docs/platform/jar-research.md": page})
        f = cc.check(d)
        warns = [x for x in f if x.rule == "untagged"]
        assert len(warns) == 1 and warns[0].line == 9 and cc.is_warning(warns[0])
        assert cc.exit_code(f) == 0


def test_skill_quote_must_match_page_rules_verbatim():
    page = "# MP\n\n## Rules\n- Mutate on the server: the client copy is a mirror [#0001].\n- Never trust a zero [#0002].\n\n## How it works\n"
    skill = "---\nname: nutrition-mp-sync\ndescription: x\n---\n## Read first\n- docs/areas/mp-sync.md\n\n## Rules quoted\n- Mutate on the server: the client copy is a mirror [#0001].\n- Never trust a zero-valued field [#0002].\n"
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1, owner="areas/mp-sync.md#rules"), _row(2, owner="areas/mp-sync.md#rules")],
              pages={"docs/areas/mp-sync.md": page}, skills={".claude/skills/nutrition-mp-sync/SKILL.md": skill})
        f = [x for x in cc.check(d) if x.rule == "skill"]
        assert len(f) == 1 and "zero-valued" in f[0].detail


def test_worked_example_paths_must_exist():
    page = "# Lua\n\n## Rules\n- x [#0001].\n\n## Worked examples\n\n| shape | file:lines | what it shows |\n|---|---|---|\n| guard | `testing/experiments/TKX_EatHook/x.lua:27-36` | the guard |\n| gone | `testing/experiments/nope.py:1-2` | nothing |\n"
    with tempfile.TemporaryDirectory() as d:
        _write(d, "testing/experiments/TKX_EatHook/x.lua", "-- lua\n")
        _tree(d, [_row(1, owner="platform/lua-platform.md#rules")], pages={"docs/platform/lua-platform.md": page})
        f = [x for x in cc.check(d) if x.rule == "example"]
        assert len(f) == 1 and "nope.py" in f[0].detail


def test_generator_drift_is_a_finding():
    lua = "-- @args (none)\n-- @reply {ok}\n-- @purpose Ping.\nTK.register(\"ping\", function() return { ok = true } end)\n"
    with tempfile.TemporaryDirectory() as d:
        _write(d, "lua/shared/PZTestKit_Core.lua", lua)
        _tree(d, [_row(1, owner="facts/x.md#a")], pages={"docs/facts/x.md": "# X\n\n## Key facts\n- a [#0001].\n"})
        import bus_inventory as bi
        text = bi.render(bi.scan(os.path.join(d, "lua")), "lua")
        _write(d, "docs/reference/harness-commands.md", text)
        assert not [x for x in cc.check(d, lua_dir=os.path.join(d, "lua")) if x.rule == "generator"]
        _write(d, "docs/reference/harness-commands.md", text + "| `zzz` | x | `y:1` | a | b | c |\n")
        assert [x for x in cc.check(d, lua_dir=os.path.join(d, "lua")) if x.rule == "generator"]


def test_section_map_and_cli_exit_code():
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1), _row(2, source="docs/vanilla/body-stats.md § Passive burn"), _row(3, status="open", kind="open")])
        m = cc.section_map(cl.read_register(os.path.join(d, "docs", "reference", "claims.tsv")))
        assert m["docs/vanilla/nutrition-core.md § X"] == ["#0001", "#0003"]
        r = subprocess.run([sys.executable, CLI, "--root", d, "--register-only"], capture_output=True, text=True)
        assert r.returncode == 0 and "0 findings" in r.stdout
        _tree(d, [_row(1), _row(1)])
        r = subprocess.run([sys.executable, CLI, "--root", d, "--register-only"], capture_output=True, text=True)
        assert r.returncode == 1 and "schema" in r.stdout


# --- R12: the two reference pages that own register rows are tag-checked; rule 4 is not run there.

def test_reference_register_pages_are_tag_checked_but_not_untagged():
    page = "# Datasets\n\n## A\n\nThe scan wrote 12 rows [#0001].\nAn untagged 99 sits here.\n"
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "testing", "artifacts", "r-20260101-000000"))
        open(os.path.join(d, "testing", "artifacts", "r-20260101-000000", "f.json"), "w").write("{}")
        _tree(d, [_row(1, grade="M", pointer="run:r-20260101-000000 f.json k", owner="reference/datasets.md#a")],
              pages={"docs/reference/datasets.md": page})
        f = cc.check(d)
        assert any(x.rule == "tag" and "#0001" in x.detail and "/M" in x.detail for x in f)
        assert not [x for x in f if x.rule == "untagged"]
        cc.fix_tags(d)
        text = open(os.path.join(d, "docs", "reference", "datasets.md"), encoding="utf-8").read()
        assert "[#0001/M]" in text
        assert not [x for x in cc.check(d) if x.rule == "tag"]


# --- provisional: a T-marker inside a mixed bracket is a provisional finding, never a missing id.

def test_mixed_bracket_provisional_is_a_tag_finding_not_a_missing_id():
    page = "# Core\n\n## Key facts\n- Burn is 0.016 [#0001, T3.7].\n"
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1)], pages={"docs/facts/nutrition-core.md": page})
        f = [x for x in cc.check(d) if x.rule == "tag"]
        assert len(f) == 1 and "provisional tag T3.7" in f[0].detail and f[0].line == 4
        assert "not in the register" not in f[0].detail
        assert not [x for x in cc.check(d, allow_provisional=True) if x.rule == "tag"]


# --- fix round 1 -------------------------------------------------------------------------------

def test_cli_survives_a_console_that_cannot_encode_page_text():
    """Rules 4 and 6 quote page text verbatim; a cp1252 console must not abort the gate."""
    page = "# P\nVerified against 42.20.4 (b0bbce05d5)\n\n## Key facts\n- one [#0001].\n\n## How it works\n\nThe drain is ≈ 0.016 per tick.\n"
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1, owner="facts/p.md#a")], pages={"docs/facts/p.md": page})
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        r = subprocess.run([sys.executable, CLI, "--root", d], capture_output=True, text=True, encoding="utf-8", env=env)
        assert r.returncode == 0, r.stderr
        assert "1 warnings" in r.stdout and "≈" in r.stdout and "UnicodeEncodeError" not in r.stderr


def test_worked_examples_are_checked_on_every_layer():
    page = "# Areas\n\n## Rules\n- x [#0001].\n\n## Worked examples\n\n| shape | file:lines | what it shows |\n|---|---|---|\n| gone | `testing/experiments/nope.py:1-2` | nothing |\n"
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1, owner="areas/mp-sync.md#rules")], pages={"docs/areas/mp-sync.md": page})
        f = [x for x in cc.check(d) if x.rule == "example"]
        assert len(f) == 1 and "nope.py" in f[0].detail


def test_cli_reports_a_bad_register_instead_of_a_traceback():
    with tempfile.TemporaryDirectory() as d:
        for mode in ("--fix-tags", "--section-map", "--view"):
            argv = [sys.executable, CLI, "--root", d, mode] + (["facts"] if mode == "--view" else [])
            r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8")
            assert r.returncode == 1, (mode, r.stdout, r.stderr)
            assert "schema" in r.stdout and "Traceback" not in r.stderr, (mode, r.stderr)


def test_malformed_aliases_file_is_a_finding_not_a_crash():
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1, grade="M", pointer="run:r-20260101-000000 f.json k")],
              aliases="nickname,run\nfoo,r-20260101-000000\n")
        f = cc.check(d, register_only=True)
        assert any(x.rule == "pointer" and "run-aliases.csv" in x.detail and "alias" in x.detail for x in f)


def test_schema_block_overflow_and_unblocked_id(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(0), _row(1)])
        f = cc.check(d, register_only=True)
        assert any(x.rule == "schema" and "#0000" in x.detail and "reserved id block" in x.detail for x in f)
    monkeypatch.setattr(cl, "BLOCKS", (("tiny", 1, 2), ("far", 10, 9999)))
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1), _row(2), _row(3)])
        f = [x for x in cc.check(d, register_only=True) if x.rule == "schema"]
        assert len(f) == 1 and "tiny" in f[0].detail and "#0003" in f[0].detail and "#0002" in f[0].detail


def test_staged_runs_the_check_when_git_cannot_answer(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        assert cc.staged_paths(d) is None                                  # a non-git directory
        _tree(d, [_row(1), _row(1)])                                       # duplicate id: the check must fail
        monkeypatch.setattr(cc, "staged_paths", lambda root: ["README.md"])
        assert cc.main(["--root", d, "--staged"]) == 0                     # nothing relevant staged
        monkeypatch.setattr(cc, "staged_paths", lambda root: ["docs/facts/x.md"])
        assert cc.main(["--root", d, "--staged"]) == 1
        monkeypatch.setattr(cc, "staged_paths", lambda root: None)         # git failed: never skip
        assert cc.main(["--root", d, "--staged"]) == 1


# --- R17: a run that left no artifact is citable only on an unverified row bounded `uncommitted:`.

def test_rule_pointer_admits_an_uncommitted_run_on_an_unverified_row():
    ptr = "run:spike-20260909-143930 findings.json sync.client_to_server"
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1, grade="M", pointer=ptr, status="unverified", bound="uncommitted: spike-20260909-143930")])
        assert not [x for x in cc.check(d, register_only=True) if x.rule == "pointer"]
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1, grade="M", pointer=ptr)])                                  # settled: still a finding
        f = [x for x in cc.check(d, register_only=True) if x.rule == "pointer"]
        assert len(f) == 1 and "spike-20260909-143930" in f[0].detail and "has no folder" in f[0].detail
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1, grade="M", pointer=ptr, status="unverified", bound="n=1")])  # wrong bound: still a finding
        f = [x for x in cc.check(d, register_only=True) if x.rule == "pointer"]
        assert len(f) == 1 and "has no folder" in f[0].detail


def test_rule_pointer_admits_an_uncommitted_run_on_a_superseded_row():
    ptr = "run:spike-20260909-143930 findings.json k"
    bound = "uncommitted: spike-20260909-143930 the boot left no artifact"
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1, grade="M", pointer=ptr, status="superseded", successor="#0125", bound=bound)])
        assert not [x for x in cc.check(d, register_only=True) if x.rule == "pointer"]
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1, grade="M", pointer=ptr, bound=bound)])                      # settled: still a finding
        f = [x for x in cc.check(d, register_only=True) if x.rule == "pointer"]
        assert len(f) == 1 and "has no folder" in f[0].detail


# --- R20: a repo: pointer may not name a tree the Phase 4 cut deletes.

def test_repo_pointers_into_the_deleted_trees_are_findings():
    with tempfile.TemporaryDirectory() as d:
        _write(d, "docs/modding/patterns.md", "# P\n")            # present today, deleted at the cut
        _write(d, "tools/x.py", "x = 1\n")
        _tree(d, [_row(1, pointer='repo:docs/modding/patterns.md:280 "x"'),
                  _row(2, pointer='repo:tools/x.py:3 "x"'),
                  _row(3, pointer='repo:docs/progress.md:5 "x"')])  # absent today, still the cut message
        f = [x for x in cc.check(d, register_only=True) if x.rule == "pointer"]
        assert len(f) == 2 and all("deleted at the cut (Phase 4)" in x.detail for x in f)
        assert any("#0001" in x.detail and "docs/modding/patterns.md" in x.detail for x in f)
        assert any("#0003" in x.detail and "docs/progress.md" in x.detail for x in f)
        assert not any("#0002" in x.detail for x in f)


def test_wall_map_is_moved_by_the_cut_not_deleted():
    with tempfile.TemporaryDirectory() as d:
        _write(d, "docs/modding/wall-map.md", "# Wall map\n")
        _write(d, "docs/modding/patterns.md", "# P\n")
        _tree(d, [_row(1, pointer='repo:docs/modding/wall-map.md:12 "x"'),
                  _row(2, pointer='repo:docs/modding/patterns.md:280 "x"')])
        f = [x for x in cc.check(d, register_only=True) if x.rule == "pointer"]
        assert len(f) == 1 and "#0002" in f[0].detail and "deleted at the cut" in f[0].detail


# --- R22: a --register part may hold a continuation slice of a block that does not start at its lo.

def test_schema_accepts_a_contiguous_continuation_slice():
    def ids(ns):
        return [_row(n, source="docs/vanilla/x.md § A", owner="facts/x.md#a") for n in ns]
    with tempfile.TemporaryDirectory() as d:       # a later slice of the post block: contiguous
        _tree(d, ids(range(2004, 2012)))
        assert not [x for x in cc.check(d, register_only=True) if x.rule == "schema"]
    with tempfile.TemporaryDirectory() as d:       # a later slice with a hole in it: still a gap
        _tree(d, ids([2004, 2006]))
        f = [x for x in cc.check(d, register_only=True) if x.rule == "schema"]
        assert len(f) == 1 and "#2005" in f[0].detail and "#2004" in f[0].detail and "gap" in f[0].detail
    with tempfile.TemporaryDirectory() as d:       # the block's own first id: the strict rule
        _tree(d, ids([2001, 2002, 2003]))
        assert not [x for x in cc.check(d, register_only=True) if x.rule == "schema"]
    with tempfile.TemporaryDirectory() as d:       # lo present with a hole after it: still a gap
        _tree(d, ids([2001, 2003]))
        f = [x for x in cc.check(d, register_only=True) if x.rule == "schema"]
        assert len(f) == 1 and "#2002" in f[0].detail


# --- R13: rule 5's directory label is bus_inventory.label_for, the one the generator itself renders.

def test_generator_label_matches_bus_inventory_label_for():
    lua = "-- @args (none)\n-- @reply {ok}\n-- @purpose Ping.\nTK.register(\"ping\", function() return { ok = true } end)\n"
    with tempfile.TemporaryDirectory() as d:
        _write(d, "lua/shared/PZTestKit_Core.lua", lua)
        _tree(d, [_row(1, owner="facts/x.md#a")], pages={"docs/facts/x.md": "# X\n\n## Key facts\n- a [#0001].\n"})
        import bus_inventory as bi
        lua_dir = os.path.join(d, "lua") + os.sep
        label = bi.label_for(lua_dir, root=d)
        assert label == "lua"
        _write(d, "docs/reference/harness-commands.md", bi.render(bi.scan(lua_dir), label))
        assert not [x for x in cc.check(d, lua_dir=lua_dir) if x.rule == "generator"]


def test_view_accepts_a_page_path(tmp_path, capsys):
    reg = tmp_path / "claims.tsv"
    rows = [dict(zip(cl.COLUMNS, ["#0001", "A.", "C", "jar:A.b @1 L2", "", "settled", "", "mechanism", "s", "facts/x.md#a"])),
            dict(zip(cl.COLUMNS, ["#0002", "B.", "C", "jar:A.c @1 L2", "", "settled", "", "mechanism", "s", "facts/xy.md#a"])),
            dict(zip(cl.COLUMNS, ["#0003", "C.", "C", "jar:A.d @1 L2", "", "settled", "", "mechanism", "s", "platform/x.md#a"]))]
    cl.write_register(str(reg), rows)
    cc.main(["--register", str(reg), "--view", "facts/x.md"])
    out = capsys.readouterr().out
    assert "#0001" in out and "#0002" not in out and "#0003" not in out
    cc.main(["--register", str(reg), "--view", "facts"])
    out = capsys.readouterr().out
    assert "#0001" in out and "#0002" in out and "#0003" not in out


def test_rules_dup_requires_byte_identical_lines_across_pages():
    area = "# A\n\n## Rules\n- Mutate on the server: the client copy is a mirror [#0001].\n- Guard the file: it runs on both sides [#0002].\n\n## How it works\n"
    plat = "# P\n\n## Rules\n- Mutate on the server: the client copy is a mirror [#0001].\n- Guard every file: it runs on both sides [#0002].\n\n## How it works\n"
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1, owner="areas/a.md#x"), _row(2, owner="platform/p.md#y")],
              pages={"docs/areas/a.md": area, "docs/platform/p.md": plat})
        f = [x for x in cc.check(d, partial=True) if x.rule == "rules-dup"]
        assert len(f) == 2 and all("#0002" in x.detail for x in f)
        assert {x.path for x in f} == {"docs/areas/a.md", "docs/platform/p.md"}


def test_rules_dup_ignores_lines_with_different_tag_sets_and_facts_pages():
    area = "# A\n\n## Rules\n- Mutate on the server: the client copy is a mirror [#0001].\n\n## How it works\n"
    plat = "# P\n\n## Rules\n- Mutate on the server: the client copy is a mirror [#0001, #0002].\n\n## How it works\n"
    fact = "# F\n\n## Key facts\n- Mutate on the server now [#0001].\n\n## How it works\n"
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1, owner="areas/a.md#x"), _row(2, owner="platform/p.md#y")],
              pages={"docs/areas/a.md": area, "docs/platform/p.md": plat, "docs/facts/f.md": fact})
        assert not [x for x in cc.check(d, partial=True) if x.rule == "rules-dup"]


def test_untagged_ignores_digits_inside_a_link_target():
    page = "# A\n\n## How it works\nThe rows sit at [the map](../reference/wall-map.md#a2-a7) for reading.\nThree rows [sit here](#a2).\n"
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1, owner="areas/a.md#x")], pages={"docs/areas/a.md": page})
        f = [x for x in cc.check(d, partial=True) if x.rule == "untagged"]
        assert not f
        page2 = "# A\n\n## How it works\nThe 3 rows [sit here](#a2).\n"
        _write(d, "docs/areas/a.md", page2)
        f = [x for x in cc.check(d, partial=True) if x.rule == "untagged"]
        assert len(f) == 1


def test_rules_dup_ignores_distinct_rules_sharing_a_tag_on_one_page():
    plat = "# P\n\n## Rules\n- Write a cite with an offset: a member list proves only a declaration [#0001].\n- Never read access off the member list: it discards the flags [#0001].\n\n## How it works\n"
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1, owner="platform/p.md#y")], pages={"docs/platform/p.md": plat})
        assert not [x for x in cc.check(d, partial=True) if x.rule == "rules-dup"]


def test_rules_dup_accepts_a_verbatim_copy_beside_sibling_rules_on_the_same_row():
    plat = "# P\n\n## Rules\n- Write a cite with an offset: a member list proves only a declaration [#0001].\n- Never read access off the member list: it discards the flags [#0001].\n\n## How it works\n"
    area = "# A\n\n## Rules\n- Keep one line here: it is not about the cite [#0002].\n- Never read access off the member list: it discards the flags [#0001].\n\n## How it works\n"
    drifted = "# A\n\n## Rules\n- Keep one line here: it is not about the cite [#0002].\n- Never read access off a member list: it drops the flags [#0001].\n\n## How it works\n"
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1, owner="platform/p.md#y"), _row(2, owner="areas/a.md#x")],
              pages={"docs/platform/p.md": plat, "docs/areas/a.md": area})
        assert not [x for x in cc.check(d, partial=True) if x.rule == "rules-dup"]
        _write(d, "docs/areas/a.md", drifted)
        f = [x for x in cc.check(d, partial=True) if x.rule == "rules-dup"]
        assert len(f) == 2 and {x.path for x in f} == {"docs/areas/a.md", "docs/platform/p.md"}
        assert all("#0001" in x.detail for x in f)


def test_untagged_ignores_a_bare_anchor_line():
    page = "# A

## How it works
<a id=\"x13\"></a>
### X13
A question with no digit.
"
    with tempfile.TemporaryDirectory() as d:
        _tree(d, [_row(1, owner="areas/a.md#x13")], pages={"docs/areas/a.md": page})
        assert not [x for x in cc.check(d, partial=True) if x.rule == "untagged"]
