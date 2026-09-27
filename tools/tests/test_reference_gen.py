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
