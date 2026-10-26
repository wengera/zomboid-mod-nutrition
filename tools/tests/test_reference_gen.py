import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import claimslib as cl
import reference_gen as rg

CONTENTS = """# Artifacts

## Contents

| Run id | File | Experiment | Cited by |
|---|---|---|---|
| `exp01-20260910-000351` | `eat-smoke.json` | `testing/experiments/s01_eat_smoke.py` | old |
| `x123-20260911-034426` | `platform-folder.json` | `testing/experiments/x123_folder.py` | old |
| `x123b-20260911-034500` | (inside `x123-20260911-034426`) | alias | old |
| `exp09-20260910-000000` | `nothing.json` | `testing/experiments/s09.py` | old |

## Reading guides
"""


def _rows():
    return [
        dict(zip(cl.COLUMNS, ["#0001", "A.", "M", "run:exp01-20260910-000351 eat-smoke.json k", "n=1", "settled", "", "mechanism", "s", "facts/eating-pipeline.md#eat"])),
        dict(zip(cl.COLUMNS, ["#0002", "B.", "M", "jar:X.y @1 L2; run:exp01-20260910-000351 eat-smoke.json k2", "n=1", "settled", "", "mechanism", "s", "facts/nutrition-core.md#update"])),
        dict(zip(cl.COLUMNS, ["#0003", "C.", "M", "run:x123b-20260911-034500 platform-folder.json boots", "n=1", "settled", "", "mechanism", "s", "platform/mod-anatomy.md#id-chain"])),
        dict(zip(cl.COLUMNS, ["#0004", "D.", "M", "run:exp01-20260910-000351 eat-smoke.json k3", "n=1", "superseded", "#0001", "mechanism", "s", "facts/eating-pipeline.md#eat"])),
        dict(zip(cl.COLUMNS, ["#0005", "The mirror says apples rot in 3 days; the code ages them by a rate.", "C", "jar:Food.update @1 L2; wiki:references/wiki-mirrors/food.md 42.20.0", "C-only; mirror wrong: apples rot in 3 days", "settled", "", "contradiction", "s", "facts/spoilage.md#walls"])),
        dict(zip(cl.COLUMNS, ["#0006", "Cooking level is not a multiplier.", "C", "jar:A.b @1 L2; wiki:references/wiki-mirrors/cooking.md 42.18.0", "C-only; mirror wrong: each level adds ten per cent", "settled", "", "contradiction", "s", "facts/cooking-and-recipes.md#walls"])),
    ]


def test_cited_by_renders_owner_pages_aliases_and_a_dash(tmp_path):
    aliases = "alias,run,file,key\nx123b-20260911-034500,x123-20260911-034426,platform-folder.json,boots.common_id\n"
    cells = rg.cited_by_cells(CONTENTS, _rows(), aliases)
    assert cells["exp01-20260910-000351"] == "[`facts/eating-pipeline.md`](../facts/eating-pipeline.md), [`facts/nutrition-core.md`](../facts/nutrition-core.md)"
    assert cells["x123-20260911-034426"] == "[`platform/mod-anatomy.md`](../platform/mod-anatomy.md)"
    assert cells["x123b-20260911-034500"] == "[`platform/mod-anatomy.md`](../platform/mod-anatomy.md)"
    assert cells["exp09-20260910-000000"] == "—"


def test_cited_by_write_and_check(tmp_path):
    p = tmp_path / "artifacts.md"; p.write_text(CONTENTS, encoding="utf-8")
    a = tmp_path / "run-aliases.csv"; a.write_text("alias,run,file,key\n", encoding="utf-8")
    assert rg.cited_by_check(str(p), _rows(), str(a)) != []          # drift: the cells still read "old"
    rg.cited_by_write(str(p), _rows(), str(a))
    assert rg.cited_by_check(str(p), _rows(), str(a)) == []
    text = p.read_text(encoding="utf-8")
    assert "## Reading guides" in text and "| `exp09-20260910-000000` | `nothing.json` | `testing/experiments/s09.py` | — |" in text


def test_contradictions_section_per_mirror_in_readme_order(tmp_path):
    readme = "# Wiki mirrors\n\n## Mirrors\n\n| File | Page |\n|---|---|\n| `cooking.md` | Cooking |\n| `food.md` | Food |\n"
    p = tmp_path / "README.md"; p.write_text(readme, encoding="utf-8")
    assert rg.contradictions_check(str(p), _rows()) != []              # no section yet
    rg.contradictions_write(str(p), _rows())
    text = p.read_text(encoding="utf-8")
    assert text.index("### cooking.md") < text.index("### food.md")
    assert "| [#0006/C/C-only] | Cooking level is not a multiplier. | each level adds ten per cent | [`facts/cooking-and-recipes.md`](../../docs/facts/cooking-and-recipes.md#walls) |" in text
    assert rg.contradictions_check(str(p), _rows()) == []
    rg.contradictions_write(str(p), _rows())                            # idempotent
    assert text == p.read_text(encoding="utf-8")


def test_cited_by_counts_both_files_a_retired_row_as_the_archive():
    """Plan 20: cited-by reads the register and its archive. A retired row lists the archive file, never the page
    it left; a superseded row, in either file, lists nothing."""
    archive = [dict(zip(cl.COLUMNS, ["#0007", "G.", "M", "run:exp09-20260910-000000 nothing.json k", "n=1; retired 2026-10-23: x",
                                     "retired", "", "mechanism", "s", "facts/old.md#gone"])),
               dict(zip(cl.COLUMNS, ["#0008", "H.", "M", "run:x123-20260911-034426 platform-folder.json k", "n=1",
                                     "superseded", "#0003", "mechanism", "s", "facts/old.md#gone"]))]
    cells = rg.cited_by_cells(CONTENTS, _rows() + archive, "")
    assert cells["exp09-20260910-000000"] == "[`reference/claims-archive.tsv`](../reference/claims-archive.tsv)"
    assert cells["x123-20260911-034426"] == "—"          # no alias given, and the superseded #0008 counts for nothing
    assert rg.contradictions_render("", _rows() + archive) == rg.contradictions_render("", _rows())


def test_read_rows_reads_the_register_then_the_archive(tmp_path):
    ref = tmp_path / "docs" / "reference"; ref.mkdir(parents=True)
    rows = _rows()
    cl.write_register(str(ref / "claims.tsv"), rows[:3])
    assert [r["id"] for r in rg.read_rows(str(tmp_path))] == ["#0001", "#0002", "#0003"]
    cl.write_register(str(ref / "claims-archive.tsv"), rows[3:4])
    assert [r["id"] for r in rg.read_rows(str(tmp_path))] == ["#0001", "#0002", "#0003", "#0004"]


GUIDED = CONTENTS.replace("| `testing/experiments/s09.py` | old |",
                          "| `testing/experiments/s09.py` ([guide](../../testing/artifacts/exp09-20260910-000000/GUIDE.md)) | old |")
GUIDED += ("\n**`exp01-20260910-000351/eat-smoke.json`** — produced by s01.\n\nHow to read it.\n\n"
           "**Skew.** A bold line inside the guide.\n\n"
           "**`x123-20260911-034426/platform-folder.json`** — produced by x123.\n\nIts guide.\n\n## Script/artifact skew\n\nOther.\n")


def test_guide_links_and_inline_guides():
    assert rg.guide_links(GUIDED) == {"exp09-20260910-000000": "../../testing/artifacts/exp09-20260910-000000/GUIDE.md"}
    assert rg.guide_rel("../../testing/artifacts/exp09-20260910-000000/GUIDE.md") == "testing/artifacts/exp09-20260910-000000/GUIDE.md"
    inline = rg.inline_guides(GUIDED)
    assert sorted(inline) == ["exp01-20260910-000351", "x123-20260911-034426"]
    assert any("A bold line inside the guide" in b for _, b in inline["exp01-20260910-000351"])
    assert not any("Other." in b for _, b in inline["x123-20260911-034426"])


def test_run_guide_reads_the_linked_file_else_the_inline_block(tmp_path):
    (tmp_path / "testing" / "artifacts" / "exp09-20260910-000000").mkdir(parents=True)
    (tmp_path / "testing" / "artifacts" / "exp09-20260910-000000" / "GUIDE.md").write_text("the file", encoding="utf-8")
    assert rg.run_guide(str(tmp_path), "exp09-20260910-000000", GUIDED) == ("testing/artifacts/exp09-20260910-000000/GUIDE.md", "the file")
    src, text = rg.run_guide(str(tmp_path), "exp01-20260910-000351", GUIDED)
    assert src == "docs/reference/artifacts.md" and "How to read it." in text
    assert rg.run_guide(str(tmp_path), "nope-20260101-000000", GUIDED) == (None, "")


def test_wildcard_keys_and_wildcard_match():
    guide = ("| `profile`; `steps[*].epoch_ms_*`, `server_*_wall` | walls | a wildcard, checked at review |\n"
             "| `phases.*.mem_before` | x | not a wildcard row? it says wildcard, so it counts |\n"
             "Every wall leaf under `phases.*` and `steps[*]` and the `store-*.json` files is a wildcard (`epoch_ms_*`).\n"
             "| `other_*` | y | no marker on this row |\n")
    assert rg.wildcard_keys(guide) == ["steps[*].epoch_ms_*", "server_*_wall", "phases.*.mem_before", "epoch_ms_*"]
    assert rg.wildcard_match("steps[*].epoch_ms_*", "steps[12].epoch_ms_before")
    assert not rg.wildcard_match("steps[*].epoch_ms_*", "steps[12].ack.epoch_ms_before")
    assert rg.wildcard_match("server_*_wall", "phases.S.server_start_wall")
    assert not rg.wildcard_match("server_*_wall", "phases.S.server_start_wallx")
    assert rg.wildcard_match("phases.*.mem_before", "phases.B.mem_before.kb")
    assert not rg.wildcard_match("phases.*.mem_before", "phases.B.mem_after")
    assert not rg.wildcard_match("epoch_ms_*", "steps[1].epoch")


def test_run_id_in_cell_keeps_an_underscored_prefix():
    # Plan 21 drivers name their runs a_pipe-…, b_actions-…: the id is the whole token, not the part after the underscore.
    assert rg.RUN_ID_IN_CELL_RX.search("`a_pipe-20261026-101003`").group(0) == "a_pipe-20261026-101003"
    assert rg.RUN_ID_IN_CELL_RX.search("`x505-20261023-085935`").group(0) == "x505-20261023-085935"
