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


def test_a_reference_link_is_checked_for_its_page_only(tmp_path):
    wire = GOOD.replace("<a id=\"formula\"></a>", "<a id=\"staircase\"></a>")
    page = GOOD.replace("- [wire](../facts/wire.md#staircase)", "- [wire](../facts/wire.md#staircase)\n- [x](../reference/experiments.md#named-experiments)")
    gone = GOOD.replace("- [wire](../facts/wire.md#staircase)", "- [wire](../facts/wire.md#staircase)\n- [x](../reference/nope.md#named-experiments)")
    root = _tree(tmp_path, {"spoilage.md": page, "a.md": gone, "wire.md": wire})
    (root / "docs" / "reference" / "experiments.md").write_text("# Experiments\n\n## Named experiments\n", encoding="utf-8", newline="\n")
    assert "link" not in _rules(_lint(root, "spoilage.md")[0])
    assert "link" in _rules(_lint(root, "a.md")[0])


def test_a_fenced_heading_is_not_a_section(tmp_path):
    quoted = GOOD.replace("- One bound [#0002/M/n=1].\n", "- One bound [#0002/M/n=1].\n\n```markdown\n## Rules\n- Do the thing [#0001].\n```\n\n")
    wire = GOOD.replace("<a id=\"formula\"></a>", "<a id=\"staircase\"></a>")
    root = _tree(tmp_path, {"spoilage.md": quoted, "wire.md": wire})
    assert _rules(_lint(root, "spoilage.md")[0]) == ["prose-floor"]


def test_a_fragment_that_is_not_a_slug_is_a_finding(tmp_path):
    wire = GOOD.replace("<a id=\"formula\"></a>", "<a id=\"staircase\"></a>")
    page = GOOD.replace("- [wire](../facts/wire.md#staircase)", "- [x](../platform/nope.md#Ownership)")
    root = _tree(tmp_path, {"spoilage.md": page, "wire.md": wire})
    details = [f.detail for f in _lint(root, "spoilage.md")[0] if f.rule == "link"]
    assert any("fragment must be a lowercase slug" in d for d in details)
    assert any("link target does not exist: ../platform/nope.md" in d for d in details)


def test_the_worked_example_header_is_the_row_before_the_separator(tmp_path):
    wire = GOOD.replace("<a id=\"formula\"></a>", "<a id=\"staircase\"></a>")
    page = GOOD.replace("## See also", "## Worked examples\n| pattern | where | what it shows |\n|---|---|---|\n| a probe | the driver | nothing |\n\n## See also")
    root = _tree(tmp_path, {"spoilage.md": page, "wire.md": wire})
    example = [f for f in _lint(root, "spoilage.md")[0] if f.rule == "example"]
    assert len(example) == 1 and "no file:lines cell" in example[0].detail


def test_the_walls_detail_names_the_stray_anchor(tmp_path):
    wire = GOOD.replace("<a id=\"formula\"></a>", "<a id=\"staircase\"></a>")
    stray = GOOD.replace("## Open\n<a id=\"open\"></a>\n", "<a id=\"open\"></a>\n## Open\n")
    root = _tree(tmp_path, {"spoilage.md": stray, "wire.md": wire})
    walls = [f for f in _lint(root, "spoilage.md")[0] if f.rule == "walls"]
    assert len(walls) == 1 and "stray <a id> above the next heading" in walls[0].detail


def test_cli_exit_codes(tmp_path):
    wire = GOOD.replace("<a id=\"formula\"></a>", "<a id=\"staircase\"></a>")
    root = _tree(tmp_path, {"spoilage.md": GOOD, "wire.md": wire})
    reg = str(root / "docs" / "reference" / "claims.tsv")
    assert pl.main([str(root / "docs" / "facts" / "spoilage.md"), "--root", str(root), "--register", reg]) == 0
    assert pl.main([str(root / "docs" / "facts" / "spoilage.md"), "--root", str(root), "--register", reg, "--cap", "3"]) == 1


OPEN_ROWS = [
    dict(zip(cl.COLUMNS, ["#0001", "Rot.", "C", "jar:A.b @1 L2", "", "settled", "", "mechanism", "s", "facts/spoilage.md#formula"])),
    dict(zip(cl.COLUMNS, ["#0002", "Is it open?", "C", "jar:A.b @1 L2", "", "open", "", "open", "s", "areas/open-questions.md#x2"])),
    dict(zip(cl.COLUMNS, ["#0003", "Also open.", "C", "jar:A.b @1 L2", "", "open", "", "open", "s", "facts/spoilage.md#open"])),
]
OPENQ = """# Open questions
%s

## Index
<a id="index"></a>
| id | question | owner | X | settled by |
|---|---|---|---|---|
| [#0002/C/open] | Is it open? | this page | X2 | a boot |
| [#0003/C/open] | Also open. | [spoilage](../facts/spoilage.md#open) | — | a read |

## Decisions
<a id="decisions"></a>
- Whether to do it — forced by the fact ([spoilage.md#open](../facts/spoilage.md#open)).

## Experiments
<a id="x2"></a>
### X2 — is it open
- Is it open? [#0002/C/open].

## See also
- [experiments](../reference/experiments.md)
""" % STAMP


def test_open_questions_has_its_own_sections_and_indexes_every_open_row(tmp_path):
    root = _tree(tmp_path, {}, rows=OPEN_ROWS)
    (root / "docs" / "areas").mkdir(parents=True)
    (root / "docs" / "facts" / "spoilage.md").write_text("# S\n" + STAMP + "\n\n## Open\n<a id=\"open\"></a>\n", encoding="utf-8")
    p = root / "docs" / "areas" / "open-questions.md"
    p.write_text(OPENQ, encoding="utf-8")
    findings, prose = pl.lint(str(p), root=str(root), partial=True)
    assert [f.rule for f in findings] == []          # no section, walls, rule-line or floor finding
    p.write_text(OPENQ.replace("| [#0003/C/open] | Also open. | [spoilage](../facts/spoilage.md#open) | — | a read |\n", ""), encoding="utf-8")
    findings, _ = pl.lint(str(p), root=str(root), partial=True)
    assert [f.rule for f in findings] == ["open-index"] and "#0003" in findings[0].detail


def test_reference_profile_checks_stamp_anchors_links_and_nothing_else(tmp_path):
    rows = [dict(zip(cl.COLUMNS, ["#0001", "A count.", "C", "data:data/x.json 2026-09-10", "snapshot 2026-09-10", "settled", "", "count", "s", "reference/datasets.md#counts"]))]
    root = _tree(tmp_path, {}, rows=rows)
    p = root / "docs" / "reference" / "datasets.md"
    p.write_text("# Datasets\n" + STAMP + "\n\n<a id=\"counts\"></a>\n## Counts\nOne count in the 2026-09-10 scan [#0001/C/snapshot].\n\n<a id=\"open\"></a>\n## Open\n- nothing.\n", encoding="utf-8")
    findings, prose = pl.lint(str(p), root=str(root), partial=True)
    assert findings == [] and prose >= 1
    p.write_text("# Datasets\n" + STAMP + "\n\n## Counts\nOne count [#0001/C/snapshot].\nIt was previously wrong.\n", encoding="utf-8")
    findings, _ = pl.lint(str(p), root=str(root), partial=True)
    assert sorted(f.rule for f in findings) == ["anchor", "narrative"]


def test_fragment_may_contain_an_underscore(tmp_path):
    root = _tree(tmp_path, {"good.md": GOOD.replace("(../facts/wire.md#staircase)", "(../reference/experiments.md#x9b_spice)")})
    (root / "docs" / "reference" / "experiments.md").write_text("# E\n", encoding="utf-8")
    findings, _ = pl.lint(str(root / "docs" / "facts" / "good.md"), root=str(root), partial=True)
    assert not [f for f in findings if f.rule == "link"]


def test_no_prose_floor_for_mod_pages_and_the_open_index(tmp_path):
    root = _tree(tmp_path, {})
    (root / "docs" / "facts" / "other-mods").mkdir(parents=True)
    p = root / "docs" / "facts" / "other-mods" / "x.md"
    p.write_text(GOOD.replace("# Spoilage", "# X"), encoding="utf-8")
    findings, _ = pl.lint(str(p), root=str(root), partial=True)
    assert not [f for f in findings if f.rule == "prose-floor"]
    q = root / "docs" / "facts" / "y.md"
    q.write_text(GOOD, encoding="utf-8")
    findings, _ = pl.lint(str(q), root=str(root), partial=True)
    assert [f for f in findings if f.rule == "prose-floor"]


def test_fragment_into_a_tagged_reference_page_is_checked(tmp_path):
    root = _tree(tmp_path, {"good.md": GOOD.replace("(../facts/wire.md#staircase)", "(../reference/datasets.md#counts)")})
    ds = root / "docs" / "reference" / "datasets.md"
    ds.write_text("# D" + chr(10) + STAMP + chr(10) + chr(10) + '<a id="counts"></a>' + chr(10) + "## Counts" + chr(10), encoding="utf-8")
    findings, _ = pl.lint(str(root / "docs" / "facts" / "good.md"), root=str(root), partial=True)
    assert not [f for f in findings if f.rule == "link"]
    (root / "docs" / "facts" / "good.md").write_text(GOOD.replace("(../facts/wire.md#staircase)", "(../reference/datasets.md#missing)"), encoding="utf-8")
    findings, _ = pl.lint(str(root / "docs" / "facts" / "good.md"), root=str(root), partial=True)
    assert [f for f in findings if f.rule == "link" and "#missing" in f.detail]


def test_fragment_into_the_wall_map_is_checked(tmp_path):
    root = _tree(tmp_path, {"good.md": GOOD.replace("(../facts/wire.md#staircase)", "(../reference/wall-map.md#g4)")})
    wm = root / "docs" / "reference" / "wall-map.md"
    wm.write_text("# W" + chr(10) + '<a id="g4"></a>' + chr(10), encoding="utf-8")
    findings, _ = pl.lint(str(root / "docs" / "facts" / "good.md"), root=str(root), partial=True)
    assert not [f for f in findings if f.rule == "link"]
    wm.write_text("# W" + chr(10), encoding="utf-8")
    findings, _ = pl.lint(str(root / "docs" / "facts" / "good.md"), root=str(root), partial=True)
    assert [f for f in findings if f.rule == "link" and "#g4" in f.detail]
