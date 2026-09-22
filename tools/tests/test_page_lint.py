import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import claimslib as cl
import page_lint as pl

STAMP = "Verified against 42.20.4 (b0bbce05d5) · 2026-09-22 · scope: a test page"
GOOD = """# Spoilage
%s

## Key facts
- Rot is a view of age [#0001].

## How it works
<a id="formula"></a>
### The formula
Age accrues per tick [#0001].

## Walls and bounds
<a id="walls"></a>
- One bound [#0002/M/n=1].
Not covered: the freezer.

## Open
<a id="open"></a>
- A question -> X7 [#0002/M/n=1].

## See also
- [wire](../facts/wire.md#staircase)
""" % STAMP


def _tree(tmp_path, pages, rows=None):
    root = tmp_path / "repo"
    (root / "docs" / "facts").mkdir(parents=True)
    (root / "docs" / "reference").mkdir(parents=True)
    rows = rows if rows is not None else [
        dict(zip(cl.COLUMNS, ["#0001", "Rot.", "C", "jar:A.b @1 L2", "", "settled", "", "mechanism", "s", "facts/spoilage.md#formula"])),
        dict(zip(cl.COLUMNS, ["#0002", "Bound.", "M", "run:exp01-20260910-003929 f.json k", "n=1", "settled", "", "bound", "s", "facts/spoilage.md#walls"]))]
    cl.write_register(str(root / "docs" / "reference" / "claims.tsv"), rows)
    for name, text in pages.items():
        (root / "docs" / "facts" / name).write_text(text, encoding="utf-8", newline="\n")
    return root


def _lint(root, name, **kw):
    return pl.lint(str(root / "docs" / "facts" / name), root=str(root), register=str(root / "docs" / "reference" / "claims.tsv"), **kw)


def _rules(findings):
    return sorted(f.rule for f in findings)


def test_a_good_page_has_no_findings(tmp_path):
    root = _tree(tmp_path, {"spoilage.md": GOOD, "wire.md": GOOD.replace("<a id=\"formula\"></a>", "<a id=\"staircase\"></a>")})
    findings, prose = _lint(root, "spoilage.md")
    assert [f for f in findings if f.rule != "prose-floor"] == []
    assert prose == 5


def test_missing_page_link_is_skipped_only_under_partial(tmp_path):
    root = _tree(tmp_path, {"spoilage.md": GOOD})
    assert "link" in _rules(_lint(root, "spoilage.md")[0])
    assert "link" not in _rules(_lint(root, "spoilage.md", partial=True)[0])


def test_missing_anchor_in_link_target(tmp_path):
    root = _tree(tmp_path, {"spoilage.md": GOOD, "wire.md": GOOD})
    assert "link" in _rules(_lint(root, "spoilage.md")[0])


def test_stamp_sections_and_order(tmp_path):
    bad_stamp = GOOD.replace(STAMP, "Verified against: 42.20.4")
    no_open = GOOD.replace("## Open\n<a id=\"open\"></a>\n- A question -> X7 [#0002/M/n=1].\n\n", "")
    swapped = GOOD.replace("## Key facts\n- Rot is a view of age [#0001].\n\n## How it works", "## How it works").replace("## See also", "## Key facts\n- Rot is a view of age [#0001].\n\n## See also")
    rules_on_facts = GOOD.replace("## Key facts", "## Rules")
    root = _tree(tmp_path, {"spoilage.md": bad_stamp, "a.md": no_open, "b.md": swapped, "c.md": rules_on_facts, "wire.md": GOOD.replace("<a id=\"formula\"></a>", "<a id=\"staircase\"></a>")})
    assert "stamp" in _rules(_lint(root, "spoilage.md")[0])
    assert "section" in _rules(_lint(root, "a.md")[0])
    assert "section" in _rules(_lint(root, "b.md")[0])
    assert "section" in _rules(_lint(root, "c.md")[0])


def test_anchor_rule_line_walls_and_narrative(tmp_path):
    no_anchor = GOOD.replace("<a id=\"formula\"></a>\n", "")
    dup_anchor = GOOD.replace("<a id=\"formula\"></a>\n", "<a id=\"formula\"></a>\n<a id=\"formula\"></a>\n")
    untagged_fact = GOOD.replace("- Rot is a view of age [#0001].", "- Rot is a view of age.")
    no_not_covered = GOOD.replace("Not covered: the freezer.\n", "")
    narrative = GOOD.replace("Age accrues per tick [#0001].", "Age accrues per tick, corrected 2026-09-10 [#0001].")
    in_code = GOOD.replace("Age accrues per tick [#0001].", "Age accrues per tick (`CONTESTED` is a word in code) [#0001].")
    wire = GOOD.replace("<a id=\"formula\"></a>", "<a id=\"staircase\"></a>")
    root = _tree(tmp_path, {"spoilage.md": no_anchor, "a.md": dup_anchor, "b.md": untagged_fact, "c.md": no_not_covered, "d.md": narrative, "e.md": in_code, "wire.md": wire})
    assert "anchor" in _rules(_lint(root, "spoilage.md")[0])
    assert "anchor" in _rules(_lint(root, "a.md")[0])
    assert "rule-line" in _rules(_lint(root, "b.md")[0])
    assert "walls" in _rules(_lint(root, "c.md")[0])
    assert "narrative" in _rules(_lint(root, "d.md")[0])
    assert "narrative" not in _rules(_lint(root, "e.md")[0])


def test_platform_rules_need_a_colon_and_a_tag(tmp_path):
    root = _tree(tmp_path, {})
    (root / "docs" / "platform").mkdir()
    page = GOOD.replace("## Key facts\n- Rot is a view of age [#0001].", "## Rules\n- Do the thing [#0001].")
    (root / "docs" / "platform" / "x.md").write_text(page, encoding="utf-8", newline="\n")
    findings, _ = pl.lint(str(root / "docs" / "platform" / "x.md"), root=str(root), register=str(root / "docs" / "reference" / "claims.tsv"), partial=True)
    assert "rule-line" in _rules(findings)


def test_prose_cap_and_worked_example_path(tmp_path):
    long_page = GOOD.replace("Age accrues per tick [#0001].", "\n".join(["Age accrues per tick [#0001]."] * 401))
    example = GOOD.replace("## See also", "## Worked examples\n| shape | file:lines | what it shows |\n|---|---|---|\n| a probe | `testing/experiments/nope.py:1-5` | nothing |\n\n## See also")
    wire = GOOD.replace("<a id=\"formula\"></a>", "<a id=\"staircase\"></a>")
    root = _tree(tmp_path, {"spoilage.md": long_page, "a.md": example, "wire.md": wire})
    assert "prose" in _rules(_lint(root, "spoilage.md")[0])
    assert "example" in _rules(_lint(root, "a.md")[0])
    assert "prose-floor" in _rules(_lint(root, "wire.md")[0])


def test_cli_exit_codes(tmp_path):
    wire = GOOD.replace("<a id=\"formula\"></a>", "<a id=\"staircase\"></a>")
    root = _tree(tmp_path, {"spoilage.md": GOOD, "wire.md": wire})
    reg = str(root / "docs" / "reference" / "claims.tsv")
    assert pl.main([str(root / "docs" / "facts" / "spoilage.md"), "--root", str(root), "--register", reg]) == 0
    assert pl.main([str(root / "docs" / "facts" / "spoilage.md"), "--root", str(root), "--register", reg, "--cap", "3"]) == 1
