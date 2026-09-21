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
