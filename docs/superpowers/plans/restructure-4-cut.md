# Restructure 4 — the cut Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the wall map and the artifacts register into `docs/reference/` with their mechanical rewrites, sweep every surviving reference to the old tree or the SDD workspace out of the pages that stay, delete the old docs, ledgers and plans by pathspec in one commit, prove the result with every lint run without `--partial`, one acceptance boot and the checker at zero, and push.

**Architecture:** One tooling task first — a small generator (`tools/reference_gen.py`) for the two generated sections the spec names (the artifacts register's `Cited by` column, the wiki mirrors' contradiction table), and the checker and lint extended to cover `reference/wall-map.md` — then four parallel tasks on disjoint files (the wall map move, the artifacts move, the reference-and-mirror sweep, the register-pass proposals), then the controller applies the register pass and makes the cut commit, then the roots are rewritten for the tree as it now stands, then the one live acceptance run, then the close. The Phase 2 and 3 procedures stay binding for any page edit; this plan's tasks carry their own particulars.

**Tech Stack:** Python 3.13 (`tools/`, `pytest`), Markdown, the claims register `docs/reference/claims.tsv` (`tools/claimslib.py`), `tools/claims_check.py`, `tools/page_lint.py`, `tools/doc_lint.py`, `tools/bus_inventory.py`, the `pzt` runner for the one acceptance run.

**Spec:** `docs/superpowers/specs/2026-09-17-reference-restructure-design.md` — § The target tree (the `reference/` files, "Deleted from the tree at the cut"), § The claims register (the `source` column; "Runs without artifacts"; "Do-not-cite"), § The checker and the generator, § Extending the reference after the cut, § What the rewritten `CLAUDE.md` carries, § Execution (Phase 4), § Acceptance (all eight), § Open questions from the draft (2: the wall map moves verbatim with one mechanical rewrite; 3: `experiments.md`; 4: dated counts). The spec itself is deleted by this plan's cut commit and stays readable at the tag `research-program-v1`.

## Global Constraints

- Spec § Execution Phase 4, verbatim: "Move `wall-map.md` with its `Ev`-cell rewrite (74 references to deleted docs become register ids) and `artifacts.md` whole with its `Cited by` regenerated; delete the old docs, ledgers and plans by pathspec in one commit; run the checker, the generator and the narrative grep; push." Spec § Open questions 2: the wall map "moves verbatim under `reference/` with one mechanical rewrite: every `Ev`-cell reference to a deleted doc becomes the register id(s) harvested from it"; `doc_lint.py` keeps the stamp and `Ev`-grade rules on it.
- Spec non-goals, verbatim: "No rewrite of the wiki mirrors. The wall map, the artifacts register and the experiment specs move with mechanical link rewrites only." A reference file therefore changes only where a link, a path, a workspace mention or a `Cited by` cell demands it, plus the one correction the Phase 1 review queued for the cut (the I13 offsets).
- Spec § Acceptance, binding at the close: (1) `python tools/claims_check.py` → 0 findings; (2) `python tools/bus_inventory.py --check` in sync and one acceptance run green; (3) every page under the contract obeys it and the narrative grep is empty under `docs/areas`, `docs/platform`, `docs/facts`; (4) ten skills ≤ 60 lines pointing at pages that exist (the fresh-session trigger test is Angus's, ruling R6 of Phase 3); (5) the tag exists on the remote and `docs/superpowers/`, `docs/progress.md`, `docs/decisions.md`, `docs/feasibility/`, `docs/vanilla`, `docs/modding`, `docs/mods-survey`, `docs/testing` are gone from `main`; (6) pytest green; (7) `claims-coverage.md` reconciles every old source; (8) every register `source` and every page link resolves from a fresh clone, no `.superpowers/` path survives in the tree — read per Phase 1 ruling R33: `grep -c '\.superpowers/' docs/reference/claims.tsv` → 0, every markdown link in the tree's pages resolves, and a `source` cell names the pre-restructure doc the row was harvested from, which a fresh clone reads at the tag.
- Implementers never edit `docs/reference/claims.tsv` (a change is a delta the controller applies, or a proposal file the controller applies with a script); never edit the old docs (they are deleted, not fixed); never run `claims_check.py --fix-tags`; never boot the game except in Task 8; the install `D:\SteamLibrary\steamapps\common\ProjectZomboid` and the workshop folder are read-only; no harness edit (comment lines in `testing/PZTestKit/` that name a deleted doc stay as they are — code and artifacts are outside acceptance 8's page-link reading).
- Every page edit under `docs/areas`, `docs/platform`, `docs/facts` follows the Phase 2 and Phase 3 procedures (`restructure-2-page-procedure.md`, `restructure-3-page-procedure.md`, deleted by the cut and readable at the tag; the rulings R1–R21 of the Phase 3 ledger bind).
- Gates before every commit: `python tools/claims_check.py --staged` → 0 (without `--partial` once the wall map has moved: every owner page then exists); `python tools/page_lint.py <the pages touched>` without `--partial` once `wall-map.md` and `artifacts.md` exist at their new paths; `python -m pytest tools/tests testing/tests -q` green (384 at the start of this plan).
- Commits: pathspec (`git add <files> && git commit -m "…" -- <files>`; a move is `git mv` then the same), succinct subjects, no Claude attribution, never `--amend`, no push (the controller pushes at the close). Implementers only on disjoint files; Opus for every implementer and reviewer; `cd /c/Users/Angus/repos/project_zomboid` in every Bash call; Windows Python takes `C:/Users/...` paths; long files through the Write tool.
- Out of scope: the mod's design; any new measurement; a rewrite of any reference file beyond the mechanical rewrites above; the Phase 4 obligations `deferred-minors-3.md` marks as later than the cut.

## Execution order

Task 1 (tools) → Tasks 2, 3, 4, 5 in parallel (disjoint files) → the controller applies the Task 5 proposals (`Register: Phase 4 pass`, with the page retags) → Task 6 (the cut commit, controller) → Task 7 (the roots after the cut) → Task 8 (the acceptance run, live) → the whole-branch final review → Task 9 (the close, controller).

## File structure

| path | responsibility |
|---|---|
| `tools/reference_gen.py`, `tools/tests/test_reference_gen.py` | `cited-by` and `contradictions`: render, `--write`, `--check` (Task 1) |
| `tools/claims_check.py`, `tools/page_lint.py`, their tests, `tools/README.md` | `wall-map.md` joins the tagged reference pages and the fragment set; a `refgen` rule (Task 1) |
| `docs/reference/wall-map.md` (from `docs/modding/wall-map.md`) | the 64-row verdict table, tagged and anchored, its old-doc references rewritten (Task 2) |
| `docs/reference/artifacts.md` (from `testing/artifacts/README.md`), a stub `testing/artifacts/README.md` | the artifacts register with `Cited by` regenerated (Task 3) |
| `docs/reference/{claims-coverage.md, experiments.md, do-not-cite.csv, tools.md}`, `references/wiki-mirrors/*.md`, `data/README.md` | the sweep (Task 4) |
| `.superpowers/sdd/restructure-4-cut/register-pass-proposals.tsv`, `register-pass-supersessions.tsv` | the register pass the controller applies (Task 5) |
| the old tree, `docs/superpowers/`, `docs/progress.md`, `docs/decisions.md`, `docs/references.md` | deleted (Task 6) |
| `CLAUDE.md`, `README.md` | the roots after the cut (Task 7) |
| `testing/experiments/_template.py` | the acceptance run id (Task 8) |
| the memory file, the ledger | the close (Task 9) |

---

### Task 1: `tools/reference_gen.py`, and the checker and lint extended to `wall-map.md`

**Files:**
- Create: `tools/reference_gen.py`, `tools/tests/test_reference_gen.py`
- Modify: `tools/claims_check.py` (`REF_TAG_PAGES` line 22; a new `rule_refgen`; `check()`; the docstring), `tools/tests/test_claims_check.py`; `tools/page_lint.py` (`REFERENCE_PAGES`), `tools/tests/test_page_lint.py`; `tools/README.md` § Reference tooling (one new entry; two entries amended)

**Interfaces:**
- Consumes: `claimslib.read_register`, `claimslib.COLUMNS`; `docs/reference/run-aliases.csv` (`alias,run,file,key`); the register's `pointer` grammar (`run:<run-id> <file> <key>`; `wiki:<mirror file> <version or date>`); the `bound` of a `contradiction` row (`mirror wrong: <the mirror's words>` after its first token).
- Produces:
  - `python tools/reference_gen.py cited-by [--page docs/reference/artifacts.md] [--write | --check]`: for every row of the page's `## Contents` table (`| Run id | File | Experiment | Cited by |`), the `Cited by` cell is rendered from the register — the owner pages (`docs/<owner page>`, as relative links from `docs/reference/`, sorted, deduplicated) of every live row whose `pointer` carries a `run:<that run id>` arm, with an alias resolved through `run-aliases.csv` (a row citing `x123b-…` counts for `x123-…`'s line and the alias line both) and `—` where no row cites the run; `--write` rewrites those cells in place and nothing else; `--check` exits 1 naming each cell that differs.
  - `python tools/reference_gen.py contradictions [--readme references/wiki-mirrors/README.md] [--write | --check]`: renders a `## Contradictions` section — a paragraph saying what the table is, then one table per mirror file in the README's `## Mirrors` order (`| Row | The code says | The mirror says | Owner |`: the register id as a full tag `[#0417/C]`, the claim, the bound's words after `mirror wrong:`, the owner page as a relative link) for every live `contradiction` row whose `wiki:` pointer names that file; the section is written between the markers `<!-- reference_gen: contradictions start -->` and `<!-- reference_gen: contradictions end -->` (created at the end of the README when absent); `--check` exits 1 on drift.
  - `claims_check.py` rule 10 `refgen`: both `--check` renders must match (a drift is a finding on the file); `REF_TAG_PAGES` includes `docs/reference/wall-map.md`. `page_lint.py` `REFERENCE_PAGES` includes `reference/wall-map.md` for the fragment check only (the page is never linted by `page_lint`; `doc_lint` keeps it).

- [ ] **Step 1: Write the failing tests**

`tools/tests/test_reference_gen.py`:

```python
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
```

Append to `tools/tests/test_claims_check.py` (the file's `_tree`/`_row`/`_write` helpers; a `refgen` finding when the artifacts page's `Cited by` drifts):

```python
def test_refgen_rule_reports_drift_in_the_artifacts_register():
    page = "# A\n\n## Contents\n\n| Run id | File | Experiment | Cited by |\n|---|---|---|---|\n| `exp01-20260910-000351` | `f.json` | `x.py` | stale |\n"
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "testing", "artifacts", "exp01-20260910-000351"))
        _tree(d, [_row(1, grade="M", pointer="run:exp01-20260910-000351 f.json k", bound="n=1")],
              pages={"docs/reference/artifacts.md": page, "docs/facts/nutrition-core.md": "# N\n\n## How it works\n<a id=\"update\"></a>\n### U\nx [#0001/M/n=1].\n"})
        f = [x for x in cc.check(d, partial=True) if x.rule == "refgen"]
        assert len(f) == 1 and "exp01-20260910-000351" in f[0].detail
```

Append to `tools/tests/test_page_lint.py` (a fragment into `wall-map.md` is checked):

```python
def test_fragment_into_the_wall_map_is_checked(tmp_path):
    root = _tree(tmp_path, {"good.md": GOOD.replace("(../facts/wire.md#staircase)", "(../reference/wall-map.md#g4)")})
    wm = root / "docs" / "reference" / "wall-map.md"
    wm.write_text("# W" + chr(10) + '<a id="g4"></a>' + chr(10), encoding="utf-8")
    findings, _ = pl.lint(str(root / "docs" / "facts" / "good.md"), root=str(root), partial=True)
    assert not [f for f in findings if f.rule == "link"]
    wm.write_text("# W" + chr(10), encoding="utf-8")
    findings, _ = pl.lint(str(root / "docs" / "facts" / "good.md"), root=str(root), partial=True)
    assert [f for f in findings if f.rule == "link" and "#g4" in f.detail]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /c/Users/Angus/repos/project_zomboid && python -m pytest tools/tests/test_reference_gen.py tools/tests/test_claims_check.py tools/tests/test_page_lint.py -q -k "refgen or cited_by or contradictions or wall_map" 2>&1 | tail -n 3`
Expected: the `reference_gen` module import fails; the `refgen` and wall-map tests fail.

- [ ] **Step 3: Implement**

`tools/reference_gen.py` (stdlib only; the docstring names both subcommands and the marker lines):

```python
#!/usr/bin/env python3
"""Generated sections of the reference (spec § The target tree): the artifacts register's `Cited by`
column and the wiki mirrors' contradiction table, rendered from the register.

    python tools/reference_gen.py cited-by [--page docs/reference/artifacts.md] [--write | --check]
    python tools/reference_gen.py contradictions [--readme references/wiki-mirrors/README.md] [--write | --check]

cited-by: for every row of the page's `## Contents` table, the `Cited by` cell lists the owner pages
of the live rows whose pointer carries `run:<run id>` (aliases from docs/reference/run-aliases.csv
count for both ids), sorted, deduplicated, as links relative to docs/reference/; `—` when none.
contradictions: one table per mirror file in the README's `## Mirrors` order, from the live
`contradiction` rows whose `wiki:` pointer names the file, between the markers
`<!-- reference_gen: contradictions start -->` / `<!-- reference_gen: contradictions end -->`.
--check exits 1 and names each drift; --write rewrites only the generated cells or section."""
```

Functions the tests name: `cited_by_cells(page_text, rows, aliases_csv_text) -> dict[run_id, cell]`; `cited_by_write(page_path, rows, aliases_path)`; `cited_by_check(page_path, rows, aliases_path) -> list[str]` (one line per drifted run id); `contradictions_render(readme_text, rows) -> str` (the section without markers); `contradictions_write(readme_path, rows)`; `contradictions_check(readme_path, rows) -> list[str]`; `main(argv)`. A live row is one whose `status` is not `superseded`. A `run:` arm is the pointer segment (split on `;`, stripped) starting `run:`; its run id is the second token. A mirror's rows are those with a `wiki:` arm whose file (second token) ends with the README's file cell. The `Cited by` link text is the owner page path without `docs/`, the target `../<owner page>` (no fragment); the contradiction table's owner link keeps the anchor and is relative to `references/wiki-mirrors/` (`../../docs/<owner>`). Table cells escape a literal `|` as `\|`.

`tools/claims_check.py`: `REF_TAG_PAGES = ("docs/reference/datasets.md", "docs/reference/tools.md", "docs/reference/wall-map.md")`; `rule_refgen(root, rows)` returns a `Finding(path, 1, "refgen", detail)` per drift line from `reference_gen.cited_by_check` on `docs/reference/artifacts.md` (skipped while the page does not exist) and `reference_gen.contradictions_check` on `references/wiki-mirrors/README.md` (skipped while the README carries no markers; a README with markers is checked for drift); `check()` appends it beside `rule_generator`; the docstring lists rule 10. `tools/page_lint.py`: `REFERENCE_PAGES = ("reference/datasets.md", "reference/tools.md", "reference/wall-map.md")` — the wall map is fragment-checked as a link target only; `main()`/`lint()` refuse to lint it as a page? No: the reference profile would run on it if passed; the close never passes it (doc_lint owns it) — add one line to the docstring saying so.

- [ ] **Step 4: Run the whole suite and the real tree**

Run: `cd /c/Users/Angus/repos/project_zomboid && python -m pytest tools/tests testing/tests -q 2>&1 | tail -n 1 && python tools/claims_check.py --partial | tail -n 1 && python tools/reference_gen.py cited-by --page testing/artifacts/README.md --check | tail -n 3`
Expected: all pass (384 + 5 = 389); the checker `0 findings` — rule 10 skips the artifacts page while it does not exist at its new path and skips the mirrors README while it carries no markers (nothing generated yet, nothing to check), so Tasks 2 and 3 stay clean before Task 4 writes the section; the CLI `contradictions --check` on a README without markers exits 1 with `section missing` (the close runs it explicitly). The `cited-by --check` against the old README path lists every drifted cell (all of them — the old cells name docs, not owners).

- [ ] **Step 5: `tools/README.md` and commit**

One entry for `reference_gen.py` (both subcommands, the markers, `--check` is rule 10); the `claims_check.py` entry gains rule 10 and the third tagged reference page; the `page_lint.py` entry says `wall-map.md` is a fragment-checked target, never a linted page. Keep each line's own ending.

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_check.py --staged --partial; git add tools/reference_gen.py tools/tests/test_reference_gen.py tools/claims_check.py tools/tests/test_claims_check.py tools/page_lint.py tools/tests/test_page_lint.py tools/README.md && git commit -m "Tools: reference_gen (cited-by, contradictions); wall-map joins the tagged reference pages" -- tools/reference_gen.py tools/tests/test_reference_gen.py tools/claims_check.py tools/tests/test_claims_check.py tools/page_lint.py tools/tests/test_page_lint.py tools/README.md
```

---

### Task 2: The wall map moves, tagged and anchored

**Files:**
- Move: `docs/modding/wall-map.md` → `docs/reference/wall-map.md` (`git mv`), then edit in place.

**Interfaces:**
- Consumes: `python tools/claims_check.py --view reference/wall-map.md` (65 rows: 64 `verdict` — one per map row, owner slug = the row id lower-cased with `+` as `-`: `a1`, `a2-a7`, `b4-b5` …, one `superseded` (`#2014`, not tagged) — and one `bound` row); `python tools/claims_check.py --section-map` (every old doc section → the ids harvested from it); the anchor plan's `## reference/wall-map.md` section (`docs/superpowers/plans/restructure-anchors.md`, the 64 slugs).
- Produces: `docs/reference/wall-map.md` — the file verbatim except: (a) every map row's `#` cell opens with `<a id="<slug>"></a> ` before the row id (`| <a id="a1"></a> A1 | …`); (b) every map row's `Ev` cell ends with the row's own register tag with its canonical suffix (`M · 12 · … [#1121/M/n=1]`; the `Ev` grammar keeps the grade first and standalone, so `doc_lint`'s `Ev`-grade rule still passes); (c) every reference to a deleted doc anywhere on the page — a markdown link (`[anatomy.md](anatomy.md)`, `(../vanilla/nutrition-core.md)`, the teardown links, `../testing/README.md`), a bare `x.md § Y` mention, or a "§ …" cross-reference into one — becomes the register id(s) harvested from that section, as a tag `[#…]` naming the one to three rows whose claims the cell relies on (found by reading the section map and the rows' claims), or, where the reference points a reader at a page rather than at a fact, a link to the page that now owns those rows (`[mod-anatomy.md#checksum-gate](../platform/mod-anatomy.md#checksum-gate)`); (d) § Sources' "The library's own documents" list names the new pages that own the map's rows (`platform/…`, `facts/…`) as links; (e) the I13 cell's fabricated offsets `@145` and `@155–@158 L162` are struck (the register's `#2008` carries the two real sites; keep the cell's other words); (f) the `../../testing/artifacts/README.md` links become `artifacts.md` (its new sibling; Task 3 moves it — the link is a forward link until then). Nothing else changes: not the header, not the row wording, not the experiments table, not the § Named experiments prose (a `-> X<N>` stays as it is).
- Rules: no row is added, dropped, merged or reworded; `.superpowers/` never appears; a rewritten reference keeps the sentence readable ("owned by `platform/mod-anatomy.md`" style where a link replaces a doc name).

- [ ] **Step 1: Move and count**

```bash
cd /c/Users/Angus/repos/project_zomboid && git mv docs/modding/wall-map.md docs/reference/wall-map.md && grep -c '^| [A-J][0-9]' docs/reference/wall-map.md && grep -o -E '(\.\./)?(vanilla|modding|mods-survey|testing)/[a-z0-9/_-]+\.md|[a-z-]+\.md( §|\)|`)' docs/reference/wall-map.md | wc -l
```

Expected: 64 rows; the count of references to rewrite (write it in the report; the spec counted 74).

- [ ] **Step 2: Anchors and tags**

A short Python over the file: for each map row line (`| <id> |` where `<id>` matches `[A-J]\d+(\+[A-J]\d+)?`), insert the anchor and append the tag from the register (`--view` gives the id and the suffix via `claimslib.canonical_suffix`). Then `python tools/claims_check.py --partial` → the 64 `owner page carries no tag` findings for `reference/wall-map.md` are gone; `python tools/claims_check.py` (no `--partial`) → `0 findings` (every owner page now exists) — if any other finding remains, report it.

- [ ] **Step 3: The reference rewrite**

By hand, reference by reference, with the section map open. Record every rewrite in the report as `<old text> -> <new text> (ids or link; the section-map line it came from)`.

- [ ] **Step 4: Gates and commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/doc_lint.py docs/reference/wall-map.md && python tools/claims_check.py | tail -n 1 && grep -c '\.superpowers/' docs/reference/wall-map.md; grep -c -E '(vanilla|modding|mods-survey|testing)/[a-z0-9/_-]+\.md' docs/reference/wall-map.md; python -X utf8 - <<'EOF'
import re, os
s = open("docs/reference/wall-map.md", encoding="utf-8").read()
for m in re.finditer(r"\]\(([^)#\s]+)", s):
    p = os.path.normpath(os.path.join("docs/reference", m.group(1)))
    if not p.startswith("http") and not os.path.exists(p): print("missing", m.group(1))
print("links checked")
EOF
git add docs/reference/wall-map.md && git commit -m "Reference: wall-map moved, tagged and anchored" -- docs/modding/wall-map.md docs/reference/wall-map.md
```

Expected: `0 finding(s)`; `0 findings, 0 warnings`; both greps `0` (the `artifacts.md` link may print `missing artifacts.md` until Task 3 lands — say so in the report); the commit records the rename (`git show --stat HEAD` shows `docs/modding/wall-map.md => docs/reference/wall-map.md`).

---

### Task 3: The artifacts register moves, `Cited by` regenerated

**Files:**
- Move: `testing/artifacts/README.md` → `docs/reference/artifacts.md` (`git mv`), then edit; Create: `testing/artifacts/README.md` (a stub).

**Interfaces:**
- Consumes: `python tools/reference_gen.py cited-by --page docs/reference/artifacts.md --write` (Task 1); the section map and `--view` for re-pointing reading-guide links; `docs/reference/run-aliases.csv` (the `x123b` alias).
- Produces: `docs/reference/artifacts.md` — the file whole, with: (a) the `## Contents` table's `Cited by` column regenerated by the tool (this alone removes every `.superpowers/` mention and every old-doc link in that column); (b) every remaining markdown link re-pointed for the new location (an artifact file link `x123-…/platform-folder.json` becomes `../../testing/artifacts/x123-…/platform-folder.json`; `../../data/README.md` stays; a link into a deleted doc becomes a link to the page that owns the rows citing that run — `python tools/claims_check.py --view <page>` and the section map decide — or, where the sentence only says "the doc that cites this", a tag naming the citing row); (c) every remaining `.superpowers/` mention in prose rewritten as a reference to the slice's report "in the SDD workspace, outside the tree" without the path; (d) the title `# testing/artifacts` becomes `# Artifacts register` and its first paragraph says the files live under `testing/artifacts/`; (e) the `x123b` alias table and every reading guide and reading restriction stay verbatim otherwise (the do-not-cite tables are already harvested into `do-not-cite.csv`, so they stay as the human-readable restrictions the spec keeps here). `testing/artifacts/README.md` (new, six lines): what the folder holds, the byte-identical rule, the local `.gitattributes` `* -text` note, and that the register of runs is `docs/reference/artifacts.md`.
- Rules: no row added or dropped; no reading guide reworded; `python tools/reference_gen.py cited-by --check` clean; every link resolves.

- [ ] **Step 1: Move, regenerate, re-point**

```bash
cd /c/Users/Angus/repos/project_zomboid && git mv testing/artifacts/README.md docs/reference/artifacts.md && python tools/reference_gen.py cited-by --page docs/reference/artifacts.md --write && python tools/reference_gen.py cited-by --page docs/reference/artifacts.md --check; grep -n '\.superpowers/' docs/reference/artifacts.md | cut -c1-160; grep -n -o -E '\]\([^)]*\)' docs/reference/artifacts.md | grep -E 'docs/(vanilla|modding|mods-survey|testing)|^[^(]*\([a-z0-9-]+-2026' | head -40
```

Then the hand edits (b)–(d), and the stub README.

- [ ] **Step 2: Gates and commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/reference_gen.py cited-by --page docs/reference/artifacts.md --check && grep -c '\.superpowers/' docs/reference/artifacts.md; grep -c -E 'docs/(vanilla|modding|mods-survey|testing)/' docs/reference/artifacts.md; python -X utf8 - <<'EOF'
import re, os
s = open("docs/reference/artifacts.md", encoding="utf-8").read()
for m in re.finditer(r"\]\(([^)#\s]+)", s):
    p = os.path.normpath(os.path.join("docs/reference", m.group(1)))
    if not m.group(1).startswith("http") and not os.path.exists(p): print("missing", m.group(1))
print("links checked")
EOF
python tools/claims_check.py --partial | tail -n 1 && git add docs/reference/artifacts.md testing/artifacts/README.md && git commit -m "Reference: artifacts register moved; Cited by regenerated" -- testing/artifacts/README.md docs/reference/artifacts.md
```

Expected: `--check` silent; both greps `0`; `links checked` alone; the checker `0 findings` (the `refgen` cited-by rule now runs on the page; the contradictions half may still report the missing mirrors section until Task 4 — say so).

---

### Task 4: The reference and mirror sweep, the data README, the contradictions table

**Files:**
- Modify: `docs/reference/claims-coverage.md`, `docs/reference/experiments.md`, `docs/reference/do-not-cite.csv`, `docs/reference/tools.md`, `references/wiki-mirrors/README.md`, `references/wiki-mirrors/{mod-structure,networking,modding,evolved-recipes}.md` (only the digests' links), `data/README.md`.

**Interfaces:**
- Consumes: the section map and `--view` for every re-pointed link; `python tools/reference_gen.py contradictions --write` (Task 1); `docs/reference/datasets.md`'s anchors (`#columns`, `#kinds`, `#counts`, `#mod-inventory`, `#workshop-rows`, `#schemas`).
- Produces, file by file:
  - `claims-coverage.md`: the 12 `.superpowers/` mentions become "the harvest workspace (kept locally, outside the tree)" wording that keeps the file name (`candidates-G1b.tsv`) as a code span without the path; the three `### .superpowers/sdd/…` headings become `### <the file's basename> (a consumed working read)`; old-doc names stay as code spans (the file is the per-old-source audit; spec acceptance 7) — any markdown link into a deleted doc becomes a code span.
  - `experiments.md`: line 44's `python .superpowers/sdd/_tools/luabalance.py` becomes `python tools/luabalance.py`; the other two mentions become "the slice-12 bounds list, consumed by the harvest" wording; every markdown link into a deleted doc becomes a link to the new owner page or a code span; the X31 wording stays (ruling R18 of Phase 3).
  - `do-not-cite.csv`: the two `why` cells' `.superpowers/` mentions become "the slice's report (workspace, outside the tree)"; every `read_instead` cell naming a deleted doc names the new owner page and anchor instead (`facts/eating-pipeline.md#fluid-path`); the CSV stays valid (quote cells that carry commas).
  - `tools.md`: the three links into `docs/mods-survey/` and `docs/modding/wall-map.md` become `../facts/other-mods/catalog.md` and `wall-map.md`.
  - `references/wiki-mirrors/README.md`: the digests' and the table's links into deleted docs become links to the new pages; then `python tools/reference_gen.py contradictions --write` appends the generated `## Contradictions` section (the markers make later runs idempotent); the four mirror files' `## Digest` links likewise (nothing else in a mirror changes: the raw wikitext is verbatim).
  - `data/README.md`: the column-authority sections (`### CSV columns`, `### Per litre, not per item`, `### JSON` under each dataset; `## mod-inventory`'s field table and `### The two nutrition signals`; `## workshop-search`'s field and row-state sections and its dated tables) are replaced by one line each pointing at the `docs/reference/datasets.md` anchor that now owns them; what stays: the intro, each dataset's one-paragraph description with its regeneration command and its stamp rule, and the `.gitattributes`/CSV notes; every link into a deleted doc becomes a code span or a link to the new page (`docs/decisions.md` mentions become "logged 2026-09-10"-style words without the file).
- Rules: no claim is reworded (the reference files are outside the contract; their sentences stay except where a path or link changes); `python tools/doc_lint.py references` → 0; `python tools/reference_gen.py contradictions --check` clean; `git grep -c '\.superpowers/' -- docs/reference references data` → nothing.

- [ ] **Step 1: The sweep, file by file**, recording every changed line in the report as `<file>:<line>: <old> -> <new>`.

- [ ] **Step 2: Gates and commits** (three pathspec commits):

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/reference_gen.py contradictions --check && python tools/doc_lint.py references && git grep -c '\.superpowers/' -- docs/reference references data; python -X utf8 - <<'EOF'
import re, os, glob
for f in ["docs/reference/claims-coverage.md", "docs/reference/experiments.md", "docs/reference/tools.md", "data/README.md"] + glob.glob("references/wiki-mirrors/*.md"):
    s = open(f, encoding="utf-8").read()
    for m in re.finditer(r"\]\(([^)#\s]+)", s):
        t = m.group(1)
        if t.startswith("http"): continue
        p = os.path.normpath(os.path.join(os.path.dirname(f), t))
        if not os.path.exists(p): print(f, "missing", t)
print("links checked")
EOF
python -c "import csv;rows=list(csv.reader(open('docs/reference/do-not-cite.csv',encoding='utf-8')));print('csv rows',len(rows),'cols',set(len(r) for r in rows))" && python tools/claims_check.py --partial | tail -n 1
git add docs/reference/claims-coverage.md docs/reference/experiments.md docs/reference/do-not-cite.csv docs/reference/tools.md && git commit -m "Reference: coverage, experiments, do-not-cite and tools follow the cut" -- docs/reference/claims-coverage.md docs/reference/experiments.md docs/reference/do-not-cite.csv docs/reference/tools.md
git add references/wiki-mirrors && git commit -m "Mirrors: digests link the new pages; contradictions table generated" -- references/wiki-mirrors
git add data/README.md && git commit -m "Data: column authority handed to reference/datasets.md" -- data/README.md
```

Expected: `--check` silent, `0 finding(s)`, the grep prints nothing, `links checked` alone (a link to `wall-map.md`/`artifacts.md` resolves once Tasks 2 and 3 land — report any that does not), the CSV one column count, the checker `0 findings`.

---

### Task 5: The register pass — proposals

**Files:**
- Create: `.superpowers/sdd/restructure-4-cut/register-pass-proposals.tsv` (`id<TAB>new_claim`), `.superpowers/sdd/restructure-4-cut/register-pass-supersessions.tsv` (`parent<TAB>successor<TAB>pages_tagging_parent`). Read-only on the register and the pages.

**Interfaces:**
- Consumes: `docs/reference/claims.tsv`; `deferred-minors-3.md` § Phase 4 register pass (the sixteen ids `#0170 #0354 #0675 #0765 #0773 #0867 #0953 #1564 #1705 #1771 #1776 #1795 #1837 #1924 #1935 #1964` and the five supersessions `#1902 -> #0717`, `#1924 -> #1571`, `#1899 -> #0640`, `#1883 -> #0618`, `#0216 -> #0611 + #0612`); `grep -rn '#<id>' docs .claude` for the pages tagging each parent.
- Produces: for each of the sixteen, the claim reworded to present tense, current truth, every number and unit kept, the slice or fix-wave clause dropped (a fact about when the reading changed is not a claim; where the clause carried a date that bounds the claim, the date moves to the sentence as a dated count); a line the controller can apply verbatim. For each supersession: the parent, the successor(s), and every page line that tags the parent (file:line), with the replacement tag the line should carry (`[#0717/C]` with its canonical suffix; a mixed bracket keeps its other ids); where a page states the parent's claim in words that the successor's claim does not cover, say so — the controller decides.
- Gate: none to run (no file under the checker's triggers changes); the report lists each proposal beside the current claim. Commit: none (the workspace is gitignored). Return the two file paths and any parent whose successor does not cover the page's sentence.

**Controller follow-up:** apply the proposals with `claimslib` (claims replaced; the five parents set `superseded` with their successors) and retag the pages in the same commit `Register: Phase 4 pass (sixteen claims present tense; five supersessions)` — then `python tools/claims_check.py` → 0 (rule 1 for the successors, rule 2 for the retags), `python -X utf8 tools/page_lint.py <the retagged pages>`.

---

### Task 6: The cut (controller)

**Files:**
- Delete by pathspec, one commit: `docs/vanilla/`, `docs/modding/`, `docs/mods-survey/`, `docs/testing/`, `docs/superpowers/` (plans, specs, this plan and its procedures included), `docs/progress.md`, `docs/decisions.md`, `docs/references.md`; `docs/feasibility/` is an empty untracked directory — remove it from disk.

- [ ] **Step 1: Pre-cut gates** — everything that must be true before the old tree goes:

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_check.py | tail -n 1 && python -X utf8 tools/page_lint.py docs/areas/*.md docs/platform/*.md docs/facts/*.md docs/facts/other-mods/*.md docs/reference/datasets.md docs/reference/tools.md | tail -n 1 && python tools/doc_lint.py docs/reference/wall-map.md references | tail -n 1 && python tools/reference_gen.py cited-by --page docs/reference/artifacts.md --check && python tools/reference_gen.py contradictions --check && python tools/bus_inventory.py --check | tail -n 1 && git grep -l -E 'docs/(vanilla|modding|mods-survey|testing)/|docs/superpowers/|docs/(progress|decisions|references)\.md' -- ':!docs/vanilla' ':!docs/modding' ':!docs/mods-survey' ':!docs/testing' ':!docs/superpowers' ':!docs/progress.md' ':!docs/decisions.md' ':!docs/references.md' ':!docs/reference/claims.tsv' ':!docs/reference/claims-coverage.md' ':!*.json' ':!*.lua' ':!*.py' && python -m pytest tools/tests testing/tests -q 2>&1 | tail -n 1 && git status --short | wc -l
```

Expected: `0 findings, 0 warnings`; page lint `0 findings` without `--partial`; doc_lint `0`; both `--check` silent; `in sync`; the `git grep` lists only `CLAUDE.md` and `README.md` (Task 7 rewrites them) — anything else is a Task 4 miss to fix first; tests green; a clean tree.

- [ ] **Step 2: The cut commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git rm -r -q docs/vanilla docs/modding docs/mods-survey docs/testing docs/superpowers docs/progress.md docs/decisions.md docs/references.md && rmdir docs/feasibility 2>/dev/null; git commit -m "Restructure 4: the cut" -- docs/vanilla docs/modding docs/mods-survey docs/testing docs/superpowers docs/progress.md docs/decisions.md docs/references.md && git show --stat HEAD | tail -n 1 && ls docs
```

Expected: the stat names only deletions; `ls docs` prints `areas facts platform reference`.

---

### Task 7: The roots after the cut

**Files:**
- Modify: `CLAUDE.md`, `README.md`.

**Interfaces:**
- Consumes: the tree as it stands after Task 6 (`ls docs`, `ls docs/reference`); `deferred-minors-3.md` § Phase 4 (the `CLAUDE.md` clauses outside § 9; the README not-mirrored row); the spec's § What the rewritten `CLAUDE.md` carries, read from the cut commit's parent (`git show <cut>~1:docs/superpowers/specs/2026-09-17-reference-restructure-design.md`; the controller's dispatch names the cut commit).
- Produces: `CLAUDE.md` without § 9 (the restructure is over; the memory file carries the history); the intro line no longer names § 9; § 3's gates as they hold now — `python tools/claims_check.py --staged` → 0 (no `--partial`), `python tools/page_lint.py <the pages touched>` (no `--partial`), `python tools/doc_lint.py docs/reference/wall-map.md references` → 0, `python tools/reference_gen.py cited-by --check` and `contradictions --check` (or the note that rule 10 runs them), `bus_inventory --check`, pytest with the dated count; § 5's artifacts clause names `docs/reference/artifacts.md` (a row there for every committed run); § 7's CRLF list without the deleted files (`file` each survivor); § 4 unchanged; one closing line in § 1 that the pre-restructure library is readable at the tag `research-program-v1`. `README.md`: the transitional line and the "moves at the cut" clause gone; `## The tree` lists `docs/reference/wall-map.md` and `artifacts.md` in their line; `## Tags` gains one line: a `source` cell names the pre-restructure doc a row was harvested from, readable at the tag `research-program-v1`; `## Sources`' `Testing_mods_in_multiplayer` row drops "not mirrored" for a plain "digested in `docs/platform/harness.md`" (or the row goes — the writer checks whether `harness.md` states what that page taught; if not, the row goes). Both LF; present tense; no program history beyond the tag line.
- Gate: the narrative grep on both files; every markdown link and code-span path resolves (the Task 12 check of Phase 3, plus the code-span check of Task 14 — both in `.superpowers/sdd/restructure-3-areas-skills-roots/task-12-brief.md` and `task-14-brief.md`, which survive in that workspace); `python tools/claims_check.py --staged` says nothing is staged under its triggers. Commit `Roots: after the cut` (both files, one pathspec commit).

---

### Task 8: The acceptance run (live)

**Files:**
- Modify: `testing/experiments/_template.py` (the `ACCEPTANCE_RUN` constant only).

This is the one game boot of the plan. One live session at a time, program-wide: the controller confirms nothing else is running before dispatching. A stray `ProjectZomboid64.exe` predating the session is the user's own client — never kill it.

- [ ] **Step 1: Doctor** — `cd /c/Users/Angus/repos/project_zomboid && python testing/pzt doctor`. Expected: every check clean. A dirty doctor stops the task: report `BLOCKED` with the output; never kill a process to make it clean.
- [ ] **Step 2: Run** — `cd /c/Users/Angus/repos/project_zomboid && python testing/pzt run --profile mod-under-test --hold 5 2>&1 | tail -40`. Expected: exit 0; the profile's `[[verify]]` probes pass; `testing/runs/<run-id>/` exists. Record `<run-id>`. If it fails: read the server and client consoles under the run directory for `tried to call nil`, `stack traceback` or a parse error naming a `PZTestKit_*.lua` file; run `python tools/luabalance.py` on the six harness files; report `FAILED` with the excerpt. Never re-run to make it pass without a fix; never edit the harness.
- [ ] **Step 3: The generated table covers the probes** — `grep -c '`trait.check`' docs/reference/harness-commands.md && python tools/bus_inventory.py --check`. Expected: at least 1, `in sync`.
- [ ] **Step 4: Record and commit** — set `ACCEPTANCE_RUN = "<run-id>"` in `testing/experiments/_template.py`; `python -m pytest testing/tests/test_template.py -q && git commit -m "Template: acceptance run id" -- testing/experiments/_template.py`. No artifact is committed: an acceptance run is provenance, not evidence. The report names the run id, the wall time and the probe acks verbatim.

---

### Task 9: Close (controller)

**Files:**
- Modify: the memory file `C:\Users\Angus\.claude\projects\C--Users-Angus\memory\pz-nutrition-mod-project.md` and its `MEMORY.md` line; the ledger.

- [ ] **Step 1: Every acceptance check, once more, without `--partial`**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_check.py | tail -n 1 && python -X utf8 tools/page_lint.py docs/areas/*.md docs/platform/*.md docs/facts/*.md docs/facts/other-mods/*.md docs/reference/datasets.md docs/reference/tools.md | tail -n 1 && grep -rnP '\b(previously|corrected 20|resolved (in|by) slice|RESOLVED 20|CONTESTED|the review found|this slice)(?![A-Za-z])' docs/areas docs/platform docs/facts README.md STRATEGY.md CLAUDE.md | wc -l && wc -l .claude/skills/*/SKILL.md | tail -n 1 && git ls-tree -d --name-only HEAD docs && git tag -l research-program-v1 && git ls-remote --tags origin research-program-v1 | wc -l && python -m pytest tools/tests testing/tests -q 2>&1 | tail -n 1 && grep -c '\.superpowers/' docs/reference/claims.tsv; git grep -c '\.superpowers/' -- ':!.gitignore' ':!*.py' | wc -l && python tools/doc_lint.py docs/reference/wall-map.md references | tail -n 1 && python tools/bus_inventory.py --check | tail -n 1 && git status --short | wc -l
```

Expected: `0 findings, 0 warnings`; `0 findings` over the 31 pages; `0`; ten files ≤ 60 lines; `docs/areas docs/facts docs/platform docs/reference` only; the tag locally and remotely (1); tests green (write the number down); the register `0`; no tracked non-code file carries a workspace path (the two `.py` mentions are code comments, ruling R33 of Phase 1); doc_lint `0`; `in sync`; a clean tree.

- [ ] **Step 2: Push, memory, ledger**

```bash
cd /c/Users/Angus/repos/project_zomboid && git push origin main && git log --oneline -1 && git status -sb | head -n 1
```

Then the memory file: the restructure is complete (Phase 4 closed at the push's head; the tree is `docs/{areas,platform,facts,reference}` plus the skills and roots; the old library at the tag); NEXT = the mod's design phase, which starts from `docs/areas/` and `STRATEGY.md` § The deliverable — outside this restructure; the literal fresh-session skill test is Angus's first check in a new session. The `MEMORY.md` line likewise. The ledger: `Task 9: complete`, `PLAN COMPLETE`. The workspace `.superpowers/sdd/restructure-4-cut/` is kept.

---

## What the whole-branch review checks

The final reviewer (Opus) reads the spec (from the cut's parent commit: `git show <cut>~1:docs/superpowers/specs/2026-09-17-reference-restructure-design.md`) § The target tree, § Execution Phase 4, § Acceptance and § Open questions 2–3, then verifies on the branch (the Phase 3 close commit `75ec6d3` to `HEAD`):

1. `docs/reference/wall-map.md` is the old file verbatim except the anchors, the tags, the reference rewrites, the § Sources list and the I13 offsets: `git diff <move>~1:docs/modding/wall-map.md HEAD:docs/reference/wall-map.md` read hunk by hunk — every hunk is one of those five kinds; every rewritten reference names ids the section map gives for that section (sample twelve); 64 rows, 64 anchors matching the register's owner slugs, 64 tags with canonical suffixes; `doc_lint` clean.
2. `docs/reference/artifacts.md` is the old file verbatim except the `Cited by` column (the tool's render, `--check` clean), the re-pointed links, the title and the workspace mentions; every reading guide and restriction intact (diff the sections); the `x123b` alias present; the stub README under `testing/artifacts/`.
3. The sweep: no `.superpowers/` path in any tracked non-code file; no link into a deleted doc anywhere under `docs/`, `references/`, `data/`, the roots or the skills (`git grep` as Task 6 Step 1); `do-not-cite.csv` valid with every `read_instead` naming a live page anchor; `data/README.md`'s column authority handed to `datasets.md` with the regeneration commands intact; the contradictions section in the mirrors README equals the tool's render and lists every live contradiction row exactly once.
4. The register pass: the sixteen claims present tense with every number kept (diff each against its old claim); the five supersessions with every page retagged (`grep -rn` for each parent id finds nothing outside the register's `successor`/`source` cells); `claims_check.py` 0.
5. The cut: `git show <cut> --stat` names only deletions under the eight paths; nothing else was deleted anywhere in the range; the tag `research-program-v1` resolves every deleted path (`git show research-program-v1:docs/modding/wall-map.md | head -n 1`).
6. The roots: `CLAUDE.md` without § 9, its gates true (run them), its paths resolving, the CRLF list true; `README.md`'s tree true of `ls`; both without program history beyond the tag line.
7. Acceptance 1–8 as the close ran them, re-run; the acceptance run's id in the ledger and in `_template.py`, its probes green in the report.
8. Rulings in the ledger: none contradicts the spec.
