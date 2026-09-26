# Restructure 3 — `areas/`, skills and roots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write the eight `docs/areas/` pages, the two tagged reference pages, the ten project skills and the three root files, so every register row owned by an `areas/` or `reference/datasets.md` / `reference/tools.md` page is stated once with its tag, every skill routes into pages that exist, and the checker is green under `--partial` with only `reference/wall-map.md` (Phase 4) outstanding.

**Architecture:** One tooling task first — the checker's cross-page `rules-dup` rule and a link-target fix for rule 4, the page lint's profiles for `areas/open-questions.md` and the two reference pages plus two small fixes — then the pages on disjoint files in two parallel waves (the reference pages and the first five area pages; then the last two area pages and the roots), then `open-questions.md` (it indexes every open row, so it comes after the area pages), then the skills (they quote the area pages' rules), then `CLAUDE.md` (it routes into pages and skills that now exist), then the close. The binding procedure is `docs/superpowers/plans/restructure-3-page-procedure.md`, which amends `restructure-2-page-procedure.md`.

**Tech Stack:** Python 3.13 (`tools/`, `pytest`), Markdown pages, the claims register `docs/reference/claims.tsv` (`tools/claimslib.py`), `tools/claims_check.py`, `tools/page_lint.py`, `tools/claims_delta.py`, Claude Code project skills (`.claude/skills/<name>/SKILL.md`).

**Spec:** `docs/superpowers/specs/2026-09-17-reference-restructure-design.md` — § The target tree (the tree, the placement rule, the sync placement, the hard cases), § The claims register (Deltas in Phases 2 and 3), § The checker and the generator (rule 6, the tag grammar), § The page contract (the options table, the writing rules, § Skills, § Coverage), § Extending the reference after the cut, § What the rewritten `CLAUDE.md` carries, § Execution (Phase 3), § Acceptance (1, 3, 4, 8), § Open questions from the draft (3: the experiments and `open-questions.md`).

## Global Constraints

- The page contract binds every `docs/areas/` page: the stamp line `Verified against 42.20.4 (b0bbce05d5) · <date> · scope: <one line>`; the sections in the contract's order (`## Rules`, `## How it works`, `## Options`, `## Walls and bounds`, `## Open`, `## Worked examples` optional, `## See also`); `## Walls and bounds` ends with a `Not covered:` line; `## Open` carries open rows with `-> X<N>` and the decisions the design must take, no recommendation.
- An options table, verbatim from the spec: "cites a wall-map row or a register id per row, marks no row preferred, recommended or chosen, lists rows in wall-map row order, and ends with the decision the design must take, as a question."
- Writing rules, verbatim from the spec: "present tense, current truth only — no 'previously', 'corrected', 'resolved in', 'the review found', no dates except the stamp and dated counts; every number outside a code block carries a tag; the number appears only on the owner page (other pages link); no run narratives (a session is cited, never described); bounds stated as facts, not as caveats about the process; an inference is written as one". Length 150–400 lines of prose for an area page; the reference pages have no cap.
- The placement rule: "in `areas/` only as a nutrition-design reading of the two layers below. A fact lives on one page (its `owner`); other pages cite the tag and never restate the number." `areas/mp-sync.md` owns no fact. The hard cases of spec § The target tree are decided as written there: an area page cites the owner and adds only the reading.
- Non-goals, verbatim: "No mod design. The areas layer says what the research established, not what the mod should be … An options table with costs and walls is research; a chosen option is design." "No new measurements."
- Tag grammar: a writer types `[#0417]` and writes the canonical suffix by hand from the register (`--fix-tags` is the controller's, R8); several ids `[#0417/M, #0512]`; no other citation form in the three layers.
- Implementers never edit `docs/reference/claims.tsv`: a row the page needs is a delta (`task-N-delta.tsv`, Phase 2 procedure § 6 and Phase 3 procedure A3) the controller applies with `tools/claims_delta.py` in a `Register: task N delta` commit before the review. An `add` of `kind` `rule` rests on register rows and mints no measurement (procedure A3); any other `add` needs evidence an old doc already states.
- Skills, verbatim from the spec: frontmatter `name`, `description` "under 1,000 characters", `paths` only where file-scoped; "Body, about 30 lines: `## Read first` (the pages in reading order, two to four), `## Rules quoted` (at most eight lines copied verbatim with their tags from those pages' `## Rules` …)"; acceptance 4: "Ten skills exist, each ≤ 60 lines, each pointing at pages that exist".
- Gates before every page commit: `python tools/claims_check.py --partial --allow-provisional` → `0 findings` (rule 4 warnings aimed at 0); `python tools/page_lint.py <page> --partial` → `0 findings`; the narrative grep empty. Gates before every tool commit: `python -m pytest tools/tests testing/tests -q` green (373 at the start of this plan).
- No game boot in this plan; the install `D:\SteamLibrary\steamapps\common\ProjectZomboid` and the workshop folder `D:\SteamLibrary\steamapps\workshop\content\108600` are read-only; no edit to the harness, drivers, probe mods, datasets, artifacts, the old docs (`docs/vanilla`, `docs/modding`, `docs/mods-survey`, `docs/testing`), the Phase 2 pages (`docs/platform`, `docs/facts` — a defect found there is a concern in the report; the controller fixes it, R9) or the anchor plan by an implementer.
- Commits: pathspec (`git add <files> && git commit -m "…" -- <files>`), succinct subjects, no Claude attribution, never `--amend`, no push (the controller pushes at the close). Implementers only on disjoint files; Opus for every implementer and reviewer; the Bash tool's cwd resets between calls (`cd /c/Users/Angus/repos/project_zomboid` first); Windows Python takes `C:/Users/...` paths; long files through the Write tool.
- Forward links: `docs/reference/wall-map.md`, `docs/reference/artifacts.md` do not exist until Phase 4 (the wall map is still `docs/modding/wall-map.md`); a page links the future path and `--partial` skips it (R7). The Phase 4 close runs every lint without `--partial`.
- Out of scope here (Phase 4): the wall-map and artifacts moves, the wiki-mirror contradiction table, the deletion of the old tree, `docs/references.md`'s removal (this plan folds its content into `README.md`; the file itself goes at the cut), the acceptance run, the fresh-session skill test in its literal form (this plan runs the proxy in Task 15).

## Execution order

Task 1 (tools, one implementer) → the controller's `#0727` correction → wave A: Tasks 2, 3, 4, 5, 6, 7, 8 in parallel (seven implementers, disjoint files) → wave B: Tasks 9, 10, 12 in parallel → Task 11 (`open-questions.md`, after every area page exists) → Task 13 (the skills, after every area page's `## Rules` is final) → Task 14 (`CLAUDE.md`, after the skills exist) → Task 15 (the close, controller). Deltas are applied by the controller between each report and its review; `--fix-tags` runs once per wave close.

## File structure

| path | responsibility |
|---|---|
| `tools/claims_check.py`, `tools/tests/test_claims_check.py` | rule `rules-dup` (cross-page byte-identical rule lines); rule 4 ignores link targets |
| `tools/page_lint.py`, `tools/tests/test_page_lint.py` | the `areas/open-questions.md` section list and `open-index` check; the `reference` profile for `datasets.md` and `tools.md`; `_` allowed in a fragment; no prose floor for `facts/other-mods/` and `open-questions.md` |
| `tools/README.md` | the two entries updated |
| `docs/reference/datasets.md`, `docs/reference/tools.md` | the two tagged reference pages (Tasks 2, 3) |
| `docs/areas/*.md` (7 + `open-questions.md`) | the area pages, one task each (Tasks 4–11) |
| `README.md`, `STRATEGY.md` | the map and the charter (Task 12) |
| `.claude/skills/<name>/SKILL.md` × 10 | the project skills (Task 13) |
| `CLAUDE.md` | the router and the operating rules (Task 14); its transitional status section (Task 15) |
| `.superpowers/sdd/restructure-3-areas-skills-roots/` | the ledger, briefs, reports, deltas, review packages, the skill-trigger transcripts |

---

### Task 1: The checker's `rules-dup` rule and the page lint's Phase 3 profiles

**Files:**
- Modify: `tools/claims_check.py` (`rule_untagged` at line 317; a new `rule_rules_dup`; `check()` at line 442; the module docstring's rule list), `tools/tests/test_claims_check.py`
- Modify: `tools/page_lint.py` (`SECTIONS`/`PAGE_SECTIONS`/`FRAGMENT_RX`/`FLOOR` near lines 30–46; `lint()` at line 77; `main()` at line 182), `tools/tests/test_page_lint.py`
- Modify: `tools/README.md` § Reference tooling (the `claims_check.py` and `page_lint.py` entries)

**Interfaces:**
- Consumes: `claimslib.iter_tags(text)` yields `(line_no, id, suffix)`; `page_lint._page_key(path, root)` returns `layer/page.md`; `page_lint._sections(lines)`; `claims_check._md_files(root, dirs)`, `claims_check._sections(text)`, `claims_check._bullets(sections, heading)`, `claims_check.Finding`, `claims_check.is_warning`.
- Produces: `python tools/claims_check.py` reports `rules-dup` findings (`<page>:<line>: rules-dup: a rule with tags #0001 differs from <other page>:<line>`); rule 4 no longer warns on a digit inside a markdown link target. `python tools/page_lint.py docs/areas/open-questions.md --partial` lints against the sections `Index`, `Decisions`, `Experiments`, `See also`, reports `open-index` for any `open` register row with no tag on the page, and applies no prose floor; `python tools/page_lint.py docs/reference/datasets.md --partial` (and `tools.md`) checks the stamp, the anchors against the register, the links and the narrative regex only, prints `prose N lines (no cap)`; a fragment may contain `_`; `facts/other-mods/*.md` draw no prose-floor warning.

- [ ] **Step 1: Write the failing tests for the checker**

Append to `tools/tests/test_claims_check.py`:

```python
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
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /c/Users/Angus/repos/project_zomboid && python -m pytest tools/tests/test_claims_check.py -q -k "rules_dup or link_target" 2>&1 | tail -n 3`
Expected: 3 failed (`rules-dup` never reported; the link-target case warns).

- [ ] **Step 3: Implement the checker changes**

In `tools/claims_check.py`:

```python
LINK_TARGET_RX = re.compile(r"\]\([^)]*\)")
RULES_DIRS = ("docs/areas", "docs/platform")


def rule_rules_dup(root):
    """Spec § The page contract: a rule that belongs to two areas appears on both pages only as the
    byte-identical line with the same tags; the checker diffs them. Lines are grouped by their
    tag-id set across docs/areas and docs/platform; a group with two different texts is a finding
    on every line of the group."""
    groups = {}
    for path in _md_files(root, RULES_DIRS):
        rel = _rel(path, root)
        for n, line in _bullets(_sections(_read(path)), "rules"):
            ids = tuple(sorted({cid for _, cid, _ in cl.iter_tags(line)}))
            if ids:
                groups.setdefault(ids, []).append((rel, n, line))
    out = []
    for ids, lines in groups.items():
        if len({l for _, _, l in lines}) > 1:
            for rel, n, _ in lines:
                others = ", ".join("%s:%d" % (r, m) for r, m, _ in lines if (r, m) != (rel, n))
                out.append(Finding(rel, n, "rules-dup", "a rule with tags %s differs from %s" % (" ".join(ids), others)))
    return out
```

In `rule_untagged`, replace `bare = CODE_SPAN_RX.sub("", line)` with `bare = LINK_TARGET_RX.sub("]", CODE_SPAN_RX.sub("", line))` (the link text stays; its target goes). In `check()`, append `+ rule_rules_dup(root)` to the second findings line (it runs whenever the page rules run, `--partial` included). Add `rules-dup` to the module docstring's rule list as rule 9.

- [ ] **Step 4: Run the checker tests**

Run: `cd /c/Users/Angus/repos/project_zomboid && python -m pytest tools/tests/test_claims_check.py -q 2>&1 | tail -n 2`
Expected: all pass. Then `python tools/claims_check.py --partial | tail -n 1` → `0 findings, 0 warnings` (the 21 Phase 2 pages carry no cross-page duplicate; if a `rules-dup` finding appears, report it — it is a real duplicate for the controller to rule on, not a test failure).

- [ ] **Step 5: Write the failing tests for the page lint**

Append to `tools/tests/test_page_lint.py` (the file's `_tree(tmp_path, pages, rows)` helper creates `docs/facts` and `docs/reference`; create other directories with `mkdir(parents=True)` where a test needs them):

```python
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
```

If the file's `_tree` helper writes pages under `docs/facts/` by the dict key and the `GOOD` page's `## See also` link is what the third test rewrites, keep the assertions as written; if the helper's signature differs, adapt the fixture calls, never the assertions.

- [ ] **Step 6: Run them to verify they fail**

Run: `cd /c/Users/Angus/repos/project_zomboid && python -m pytest tools/tests/test_page_lint.py -q -k "open_questions or reference_profile or underscore or no_prose_floor" 2>&1 | tail -n 3`
Expected: 4 failed.

- [ ] **Step 7: Implement the page lint changes**

In `tools/page_lint.py`:

```python
PAGE_SECTIONS = {
    "platform/overview.md": ["Rules", "How it works", "Coverage", "Open", "Worked examples?", "See also"],
    "areas/open-questions.md": ["Index", "Decisions", "Experiments", "See also"],
}
REFERENCE_PAGES = ("reference/datasets.md", "reference/tools.md")   # tagged owners outside the contract's section shape
NO_FLOOR = ("facts/other-mods/", "areas/open-questions.md")           # the mod pages' Key facts are one line per technique; the index is rows
FRAGMENT_RX = re.compile(r"^[a-z0-9_-]+$")
```

In `lint()`: compute `reference = key in REFERENCE_PAGES`; when `reference`, skip the section checks (unknown / missing / order), the rule-line checks, the `Walls and bounds` closer, and the cap and floor (return `prose` still counted); keep the stamp, the anchor checks, the narrative check and the link checks. When `key == "areas/open-questions.md"`, after the anchor checks: for every register row with `status == "open"`, if its id is not in `{cid for _, cid, _ in cl.iter_tags(text)}`, append `Finding(rel, 1, "open-index", "%s (%s) is open but not indexed on this page" % (r["id"], r["owner"]))`. Replace `elif prose < FLOOR:` with `elif prose < FLOOR and not key.startswith(NO_FLOOR):`. In `main()`, print `(no cap)` for a reference page instead of `(cap N)`. Update the module docstring (the profiles, the two rules).

- [ ] **Step 8: Run the whole suite and the real pages**

Run: `cd /c/Users/Angus/repos/project_zomboid && python -m pytest tools/tests testing/tests -q 2>&1 | tail -n 2 && python -X utf8 tools/page_lint.py docs/platform/*.md docs/facts/*.md docs/facts/other-mods/*.md --partial | tail -n 1`
Expected: all pass (373 + 7 = 380); the 21 pages `0 findings, 0 warnings` (the two floor warnings on `beyondten` and `itemquality` are gone).

- [ ] **Step 9: `tools/README.md`**

In the `claims_check.py` entry add rule 9 (`rules-dup`: `## Rules` lines under `docs/areas` and `docs/platform` grouped by tag-id set must be byte-identical) and the rule 4 note (a digit inside a markdown link target is not a number). In the `page_lint.py` entry add the `areas/open-questions.md` profile (`Index`, `Decisions`, `Experiments`, `See also`; `open-index`; no floor), the `reference` profile (`datasets.md`, `tools.md`: stamp, anchors, links, narrative; no sections, no cap), the underscore in fragments, and the `facts/other-mods/` floor exemption. Keep the file's line endings as they are (check with `file tools/README.md`; edit line-based).

- [ ] **Step 10: Commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_check.py --staged; git add tools/claims_check.py tools/page_lint.py tools/tests/test_claims_check.py tools/tests/test_page_lint.py tools/README.md && git commit -m "Tools: rules-dup rule, link targets in rule 4, page_lint Phase 3 profiles" -- tools/claims_check.py tools/page_lint.py tools/tests/test_claims_check.py tools/tests/test_page_lint.py tools/README.md
```

**Controller follow-up (not the implementer):** the Phase 1 obligation on `#0727` — its second pointer `data:testing/artifacts/exp06-20260910-112726/recipes.json` is a committed artifact file and belongs in the `run:` form: read `testing/artifacts/exp06-20260910-112726/recipes.json`, find the key that holds the five live ingredient lists, and rewrite the pointer as `run:exp06-20260910-112726 recipes.json <key>` in a `Register: correction (#0727 pointer)` commit; `python tools/claims_check.py --register-only` → 0.

---

### Task 2: `docs/reference/datasets.md`

Follows the Phase 3 procedure (A1, A8, A11, A12) and the Phase 2 procedure it amends. Particulars:

- Rows 153: count 61, mechanism 42, rule 21, table 8, bound 8, open 7, tool 5, order 1; 140 settled, 7 open, 6 superseded (not tagged). Anchors, from the anchor plan § `reference/datasets.md`, in this order: `#columns` (46 rows), `#kinds` (7), `#counts` (32), `#mod-inventory` (31), `#workshop-rows` (11), `#schemas` (18), `#fidelity-links` (no rows; links to the `facts/` rows that measured the datasets against the game, owns no number), `#open` (8).
- Source: `data/README.md` (986 lines: § food-items with its CSV columns, the per-litre rule, the JSON; § recipes; § evolved-recipes; § mod-inventory with the two nutrition signals; § workshop-search with its dated tables). The column authority moves here whole: every column's meaning as the README states it. The eight `table` rows carry their tables verbatim minus `Ev`/`Cite` columns and inline citations (R10, R12); the dated tables of § workshop-search are `count` rows stated with their sweep stamp in the sentence.
- Every `count` row's sentence carries its date ("in the 2026-09-10 17:47 sweep"); every `snapshot` bound is stated in words; the `mod-inventory` partial-view caveat on any zero (`live_media`, `media_at`) is stated as a fact at `#mod-inventory`.
- Hands off: a dataset's fidelity against the game (the sums, the live ingredient lists) is `facts/cooking-and-recipes.md#dataset-fidelity` and `facts/food-item-model.md` — `#fidelity-links` links them and states no number; the tools that produce the datasets are `reference/tools.md` (link; the tool rows owned here are the ones whose claim is about the data, not the script).
- Gate: `python tools/page_lint.py docs/reference/datasets.md --partial` under the reference profile (Task 1), `claims_check.py --partial --allow-provisional`, the narrative grep. Commit `Reference: datasets`.

### Task 3: `docs/reference/tools.md`

Follows the Phase 3 procedure (A1, A8, A11, A12). Particulars:

- Rows 45: tool 22, mechanism 12, table 3, rule 3, bound 2, count 2, open 1; 42 settled, 1 open (`#0783`), 2 unverified (`#0865`, `#1839` — `## Open` lines stating their numbers, R15/R16, and nowhere else on the page). Anchors in the anchor plan's order: `#doc-lint` (4), `#mod-lint` (15, the nine rules with their engine standing — the `mod_lint` table verbatim under its `table` row), `#mod-inventory-tool` (4), `#food-scan` (5), `#recipe-scan` (3), `#workshop-search` (8), `#wiki-mirror` (2), `#claims-tools` (2), `#conventions` (1), `#open` (1 + the two unverified).
- Sources: `tools/README.md` (§ Intake pipeline for the scanners, § Reference tooling for the claims tools), `docs/testing/profiles.md` § L0 for `mod_lint.py`'s standing.
- `#claims-tools` states the register grammar in the tree, per procedure A8 (the nine pointer forms including `web:`, `%20`, the on-disk `mod:` form, `lua:` relative to `media/`, the three readings of `data:`), in words, as conventions; the tools' rules are the spec's, not claims, so that prose carries no tag. It names `tools/claims_delta.py` and `tools/page_lint.py` beside the five the anchor plan lists (they exist now) in one line each: what each reads and writes and when it must run.
- Gate as Task 2. Commit `Reference: tools`.

### Task 4: `docs/areas/new-nutrients.md`

Follows the Phase 3 procedure (A2–A6, A11, A12). Particulars:

- Rows owned: 1 (`#0186`, rule, `#effect-paths`). Anchors, in order under their sections: `## Options` → `#store-options` (character modData, item modData, global modData, a parallel Lua store, a script key), `#effect-paths` (the moodle surface, the weight model, the item pass, the eat hooks); `## How it works` → `#sync-route`, `#persistence`; `#walls`, `#open`.
- Cites: `platform/mp-model.md` (ownership, the wire routes, wipe-and-replace, the command bus), `facts/wire-packets.md` (the field contracts: which packet carries what, the measured desyncs), `platform/lua-platform.md#registries` (the moodle walls), `facts/body-and-weight.md` (the weight model's inputs), `facts/nutrition-core.md` (the store clamps), `facts/other-mods/beyondten.md` and `simplestatus.md` (a mod nutrient banked in modData, the transmit wipe); the wall map's A rows (new nutrient fields), C (the weight formula), D (moodles), G (traits) by register id.
- Walls: X4 as a wall ("the trait sync path is untraced", citing its open row and linking `open-questions.md#x4`); the moodle walls by citation; what a client copy is not. Open: the store and clamp decisions the design must take; X14, X28, X25 where the rows name them.
- Cap 400. Commit `Page: areas/new-nutrients`.

### Task 5: `docs/areas/item-pass.md`

Follows the Phase 3 procedure. Particulars:

- Rows owned: 8 — `#0255` (rule), `#1001` (table: the five routes, verbatim from `docs/modding/item-overrides.md` § The five routes minus the `Ev` column) at `#route-options`; `#1017` (rule) at `#minimal-block`; `#1030` (bound) at `#scope`; `#1019` (count), `#1050`, `#1057` (rules), `#1674` (verdict) at `#walls`. Anchors: `## Options` → `#route-options` (a `module Base` re-declaration, a per-item override block, an eat or cook Lua hook, item modData — the table's rows cite the J rows and `#1001`); `## How it works` → `#minimal-block`, `#scope` (the counts are `reference/datasets.md#counts` — link, never restate); `#walls`, `#open`.
- Cites: `platform/loader-and-scripts.md#per-key-merge` (the merge, the sorted replay, the same-path drop — cite, never restate), `facts/food-item-model.md` (the keys and what the loader does with each), `facts/eating-pipeline.md` (what an override changes downstream), `facts/other-mods/longtermpreservation.md` (a mod's own-module foods), the wall map's I and J rows.
- Walls: the identity reset on append, the same-path drop, the absent corpus precedent (`#1674`, `#1019` with their snapshot date), the dataset unit traps (link `datasets.md#columns`), the display-name weight guard, X15 and X33 by their open rows. Open: mod-added foods in or out (the decision); X15, X19, X20, X33.
- Cap 400. Commit `Page: areas/item-pass`.

### Task 6: `docs/areas/eat-and-cook-hooks.md`

Follows the Phase 3 procedure. Particulars:

- Rows owned: 0. Anchors: `## Options` → `#hook-options` (`OnEat`, a `server/` wrapper of `ISEatFoodAction.complete`, `OnCooked`, `OnCreate`: side, what each can still change, cost, wall); `## How it works` → `#side-choice`, `#seat-in-the-order` (which seats see pre-intake and which post-intake values, citing the eat order block on `facts/eating-pipeline.md#eat` — never carrying the block), `#cook-seat`; `#walls`, `#open`.
- Cites: `platform/lua-platform.md#script-hooks` (dispatch mechanics: how the hooks resolve, which side calls each, `EatOnClient` applies no numbers, the `server/` wrapper runs before `Eat` — the hard case: cite, never restate), `facts/eating-pipeline.md` (the order of writes, the packets `Eat` sends, partial eating, the fluid path), `facts/cooking-and-recipes.md` (the cook block, type-change deltas), `facts/other-mods/autocook.md`, the wall map's B and F rows.
- Walls: X13 as a wall (the drink path's interceptability is unmeasured), the hooks this build does not offer by citation. Open: X24, X31, X33 and the decisions each would settle; X9b where the cook seat names it.
- Cap 400. Commit `Page: areas/eat-and-cook-hooks`.

### Task 7: `docs/areas/mp-sync.md`

Follows the Phase 3 procedure. Particulars:

- Rows owned: 1 (`#0128`, rule, `#sync-options`). The page owns no fact (spec § Sync placement): every mechanism is a citation of `platform/mp-model.md` and every field contract a citation of `facts/wire-packets.md`. Anchors: `## Options` → `#sync-options` (the command bus, `transmitModData`, script data loaded per side); `## How it works` → `#authority`, `#failure-modes` (citing the mechanism rows, never restating them); `#walls` (each line citing its wall-map row), `#open`.
- Cites: `platform/mp-model.md` (every anchor), `facts/wire-packets.md` (the desyncs, the staircase, the cooked-thirst halving), `platform/lessons.md` (the sync rules — copied byte-identically into `## Rules` where they belong to this area, A3.1), `facts/other-mods/simplestatus.md` (the wipe), the wall map's E rows.
- Open: the sync questions a run must settle before the design fixes a route (X14, X27, X28); the authority decisions.
- Cap 400. Commit `Page: areas/mp-sync`.

### Task 8: `docs/areas/ui-and-moodles.md`

Follows the Phase 3 procedure. Particulars:

- Rows owned: 1 (`#1114`, rule, `#read-cadence`). Anchors: `## Options` → `#surface-options` (a client panel, a moodle through MoodleFramework, tooltip and translation text); `## How it works` → `#moodle-route` (MoodleFramework as the only route and what adopting it costs; the registry mechanism is `platform/lua-platform.md#registries` — cite, restate nothing), `#read-cadence`, `#honest-but-wrong` (citing the staircase and cooked-thirst rows on `facts/wire-packets.md`); `#walls`, `#open`.
- Cites: `platform/lua-platform.md#registries` (the two moodle walls, the trait registry), `platform/mod-anatomy.md` (translations, the dedicated server resolving no display name), `facts/wire-packets.md`, `facts/other-mods/simplestatus.md` (a viewer's read cadence), `facts/other-mods/catalog.md` (MoodleFramework's registration surface), the wall map's D, G and H rows.
- Walls: X29 ("no measured moodle route exists"), X4 ("the trait sync path is untraced"), X5 (the translation override is unmeasured) — each as a wall citing its open row and linking `open-questions.md#x<n>`. Open: X29, X4, X5, X2 and the decisions the derived-UI question forces.
- Cap 400. Commit `Page: areas/ui-and-moodles`.

### Task 9: `docs/areas/packaging.md`

Follows the Phase 3 procedure. Particulars:

- Rows owned: 0. Anchors: `## How it works` → `#layout`, `#checksum-plan` (what this mod does about the three gate arms and byte-identical files on both sides; the arms themselves are `platform/mod-anatomy.md#checksum-gate` — cite), `#resident-stack`, `#shelf-life`; `## Options` → `#compat-options` (shadow, `common/` split, a patch mod, do nothing); `#walls`, `#open`.
- Cites: `platform/mod-anatomy.md` (the id chain, version dirs, `common/`, the checksum gate, the missing-mod failure mode, build pinning), `platform/loader-and-scripts.md` (the file map, the same-path drop), `platform/lessons.md#corpus-drift`, `facts/other-mods/catalog.md` (the resident mods and what each touches), the wall map's I rows.
- Walls: the packaging limits inherited by citation; X16 by its open row. Open: X16, X20, X21, X22 and the packaging decisions; the uninstalled Workshop neighbours that block them (cite the catalog rows).
- Cap 400. Commit `Page: areas/packaging`.

### Task 10: `docs/areas/testing-your-mod.md`

Follows the Phase 3 procedure. Particulars:

- Rows owned: 1 (`#0179`, rule, `#scenario-inputs`). Anchors: `## How it works` → `#mod-profiles` (the profiles this mod will ship, seeded from `testing/profiles/mod-under-test.toml` and the schema on `platform/harness.md#profiles` — link the schema, restate no key), `#mod-scenarios`, `#verify-rows`, `#scenario-inputs`, `#owned-experiments` (X4, X5, X13, X29: what each settles and what it costs — the costs are `reference/experiments.md` § Owners and the cost roll-up, linked, never restated as numbers), `#grading`, `#sandbox` (the sandbox roll-up table: every option this mod's evidence depends on with the value each run used — carried from the rows the `facts/` pages own by citation; a table whose cells are tags and option names, no bare number); `## Options` (the anchor plan names none — one table, the three ways a nutrition scenario can be paced: real time, `DayLength`, the time-speed command, each citing its row on `platform/harness.md`, ending with the pacing decision as a question); `#walls`, `#open`.
- Cites: `platform/harness.md` (the instrument — every mechanism), `docs/reference/harness-commands.md` (the generated command table; link without a fragment), `facts/nutrition-core.md` (the three-day verification), `facts/wire-packets.md#staircase`, the wall map's rows the owned experiments settle.
- Walls: what this plan cannot test on this machine, each with its bound (one client, one fixture, no second machine). Open: the measurements the plan still owes.
- Cap 400. Commit `Page: areas/testing-your-mod`.

### Task 11: `docs/areas/open-questions.md` — written after Tasks 4–10

Follows the Phase 3 procedure A7. Particulars:

- Rows owned: 55 at the 26 `#x<n>` anchors — 44 `open` (tagged at their anchor) and 11 `superseded` (not tagged; the subsection says in one clause what the successor settled, citing it). Anchors: `#index`, `#decisions`, then `#x2`, `#x4`, `#x5`, `#x7`, `#x9b`, `#x13`–`#x33` in the anchor plan's order, each `<a id>` + `### X<N> — <question>` under `## Experiments`.
- `## Index`: one row per `open` row in the register (117 at the plan's writing: areas 44, facts 36, platform 26, reference 11 — count again with `python -c` over `claimslib.read_register` at writing time), ordered by id, cells: the full tag, the claim verbatim, the owner page as a link to its `#open` (or its anchor for a reference page), the `X` id or `—`, the settling check in one clause. The page lint's `open-index` rule fails any open row missing.
- `## Decisions`: one line per decision line on the seven area pages' `## Open` (read them; link each page's `#open`).
- `## See also`: `reference/experiments.md`, the seven area pages, `platform/overview.md#coverage`.
- No prose floor; the narrative grep applies. Commit `Page: areas/open-questions`.

### Task 12: `README.md` and `STRATEGY.md`

Follows the Phase 3 procedure A10. **Files:** Modify `README.md` (rewrite), `STRATEGY.md` (rewrite). Read first: `docs/references.md` (folded in here), `docs/platform/overview.md` § Coverage, the spec § The target tree (the tree listing) and § Coverage (the one-line form).

- `README.md` (about 90 lines): the title; what the repo is (an agent-facing reference for PZ Build 42 modding, the nutrition mod its first consumer, every claim tagged to a register row with its evidence pointer); the build line (`42.20.4`, jar `b0bbce05d5`, dedicated-server multiplayer, single-player never claimed); `## Reading order` (`CLAUDE.md` routes a task to pages; `docs/areas/` the nutrition lens, `docs/platform/` general modding knowledge, `docs/facts/` measured mechanics, `docs/reference/` the register, datasets, tools, experiments, the generated harness commands); `## The tree` (the target tree's directory list as it stands after this plan, one line per directory and root file; `docs/reference/wall-map.md` and `artifacts.md` named as moving at the cut; one transitional line naming `docs/vanilla`, `docs/modding`, `docs/mods-survey`, `docs/testing` as the pre-restructure docs, readable until the cut and forever at the tag `research-program-v1`); `## Tags` (the grammar in five lines: `[#0417/M/n=1]` → `docs/reference/claims.tsv` row, grade, bound token, status; the register columns; `python tools/claims_check.py`); `## Coverage` (the one-line form: "`docs/platform/` is not a modding manual …", linking `docs/platform/overview.md#coverage`); `## Sources` (from `docs/references.md`: the mirrored wiki pages as a table `page · mirror · why`, only rows with a mirror or a digest; the ecosystem projects as a short list without status glyphs; the internal sources line); `## Related workspace` (the disassembler at `C:\Users\Angus\pz-b42`, read-only, used through `pz.sh`). No status legend, no `☐`/`◐`/`●`, no to-do rows.
- `STRATEGY.md` (about 40 lines): the title and the charter line; `## The mod` verbatim from today's file; `## The deliverable` rewritten: the library is built and is the reference this repository now is; the design comes next and is not in this tree; the charter's rule that the reference states what the research established and never what the mod should be; `## Method rules` — the five rules kept and reworded to the tree (ground truth is the local install and the jar; every claim carries a register tag with its grade and pointer; the wiki is a mirror and a digest, never the authority; external sources live in `README.md` § Sources; the pz-b42 workspace is reused, never duplicated); one closing line: standing warnings are rules on `docs/platform/lessons.md`. Drop § Pillars, § Phases and § Standing warnings.
- Gate: the narrative grep on both files; every path named exists:

```bash
cd /c/Users/Angus/repos/project_zomboid && python -X utf8 - <<'EOF'
import re, os
for f in ("README.md", "STRATEGY.md"):
    for m in re.finditer(r"\]\(([^)#\s]+)", open(f, encoding="utf-8").read()):
        p = m.group(1)
        if not p.startswith("http") and not os.path.exists(p): print(f, "missing", p)
print("checked")
EOF
```

Expected: `checked` alone. Commit `Roots: README and STRATEGY` (both files in one pathspec commit).

### Task 13: The ten skills — after Task 11

Follows the Phase 3 procedure A9. **Files:** Create `.claude/skills/pz-modding-platform/SKILL.md`, `pz-jar-research/SKILL.md`, `pz-mod-testing/SKILL.md`, `nutrition-new-nutrients/SKILL.md`, `nutrition-item-pass/SKILL.md`, `nutrition-eat-and-cook-hooks/SKILL.md`, `nutrition-mp-sync/SKILL.md`, `nutrition-ui-and-moodles/SKILL.md`, `nutrition-packaging/SKILL.md`, `nutrition-testing-your-mod/SKILL.md`.

- Per skill: `## Read first` — `pz-modding-platform`: `docs/platform/overview.md`, then the platform page the task's surface names (`mod-anatomy`, `loader-and-scripts`, `lua-platform`, `mp-model`), `docs/platform/lessons.md`; plus a `## Coverage` section quoting `platform/overview.md` § Coverage's opening four sentences verbatim; its description names the surfaces (weapons, UI, world, vehicles, sounds, tiles, a mod that is not about food or nutrition) and says it does not fire on a nutrition task. `pz-jar-research`: `docs/platform/jar-research.md`, `docs/reference/jar-method-notes.md`; description: a question that needs the jar (`pz.sh grep|methods|refs|dump`, a class, a member, an offset, "what does the engine do when"). `pz-mod-testing` (`paths: ["testing/**"]`): `docs/platform/harness.md`, `docs/reference/harness-commands.md`, `docs/areas/testing-your-mod.md`; description: `pzt`, a profile, `TK.register`, a driver, a live run, `testing/artifacts/`. Each `nutrition-<area>`: its area page first, then the two pages its `## See also` rests on; description: the area's identifiers (the anchors' nouns: `transmitModData`, `ItemStatsPacket`, `module Base`, `OnEat`, `MoodleFramework`, `mod.info`, `[[verify]]` …), key use case first.
- `## Rules quoted`: at most eight lines, byte-identical to lines in the Read-first pages' `## Rules` (copy with the Read tool; the checker's rule 6 diffs them), chosen for the hazards an agent meets before it reads. `## Also`: two or three cross-page pointers.
- Every file ≤ 60 lines; every description < 1,000 characters; a skill states no number and duplicates no page.
- Gate: `python tools/claims_check.py --partial` → `0 findings` (rule 6); `wc -l .claude/skills/*/SKILL.md`; `python -X utf8 -c "import re,glob;[print(f,len(re.search(r'description:\s*(.*)',open(f,encoding='utf-8').read()).group(1))) for f in glob.glob('.claude/skills/*/SKILL.md')]"`. Commit `Skills: the ten project skills` (all ten files in one pathspec commit).

### Task 14: `CLAUDE.md` rewritten — after Task 13

Follows the Phase 3 procedure A10 and the spec § What the rewritten `CLAUDE.md` carries. **Files:** Modify `CLAUDE.md` (rewrite; LF; about 130 lines). Read first: today's `CLAUDE.md` (every rule it carries is either kept, moved to a page, or dropped with a reason in the report), the spec section, `docs/platform/overview.md` (§ Coverage and `#routing`), `docs/platform/lessons.md` (the rules the gotchas move to), the ten skills' names.

Sections, in the spec's order, then one transitional section:

1. `## 1. What this repo is` — the reference tree and the mod, in four lines; then the router table `task shape → pages in reading order` with at least these rows: add a mod nutrient → `areas/new-nutrients` → `platform/mp-model` → `facts/wire-packets`; override a vanilla food → `areas/item-pass` → `platform/loader-and-scripts` → `facts/food-item-model`; hook eating or cooking → `areas/eat-and-cook-hooks` → `platform/lua-platform#script-hooks` → `facts/eating-pipeline`; sync mod state → `areas/mp-sync` → `platform/mp-model` → `facts/wire-packets`; show a value or a moodle → `areas/ui-and-moodles` → `platform/lua-platform#registries`; package or ship → `areas/packaging` → `platform/mod-anatomy`; test a mod live → `areas/testing-your-mod` → `platform/harness` → `reference/harness-commands`; answer from the jar → `platform/jar-research` → `reference/jar-method-notes`; a PZ modding task outside nutrition → `platform/overview#coverage` → the platform page; a dataset column → `reference/datasets`; a tool → `reference/tools`; what is still open → `areas/open-questions` → `reference/experiments`; and the line that the skills under `.claude/skills/` route the same way.
2. `## 2. Ground truth` — the install and the workshop folder read-only, always; the jar toolchain at `C:\Users\Angus\pz-b42`; dedicated-server MP evidence, single-player never claimed; the build and jar hash.
3. `## 3. Gates before any commit` — `python tools/claims_check.py --staged` → 0; `python tools/page_lint.py <the pages touched> --partial` (without `--partial` from the Phase 4 close on); `python tools/bus_inventory.py --check`; `python tools/doc_lint.py docs/reference/wall-map.md` (the file moves at the cut; until then the two doc_lint lines today's § 6 carries); pytest green with the dated count (the number Task 1 leaves).
4. `## 4. Extending the reference` — one line per item of spec § Extending the reference after the cut (seven).
5. `## 5. Harness rules` — verbatim in substance from the spec's item (5): `pzt doctor` before every boot; one live game session at a time; never `-safemode`; harness changes before the run in their own commit with the balance check and the regenerated command table; a driver never edited after its run; readings that come back trivial, unmeasured or falsified are written as such; artifacts byte-identical with a row in the artifacts register; a raising probe gated on the server with `[client] timeout` low and `pzt run` expected to fail; a stray `ProjectZomboid64.exe` predating a session is the user's own client, never killed; fixture caches per-machine and gitignored; the Kahlua rules (no `goto`, no `%d` on floats, no `#` on Java lists).
6. `## 6. Process` — SDD with fresh Opus implementers and reviewers, Fable lead, no silent downgrade (wait for the reset or ask); the skill path and its scripts (`sdd-workspace`, `task-brief`, `review-package`); per-plan ledgers `.superpowers/sdd/<plan-basename>/progress.md` are the only ledgers, kept, never deleted; rulings written `Ruling: <what> — <why> — cost if wrong: <…>`; a ruling about the platform becomes a rule on `platform/lessons.md` with its mechanism row, a ruling about how this repository works becomes a rule here, nothing is a ledger row; pathspec commits; never `--amend`; no Claude attribution; succinct messages; proceed to completion and ledger decisions instead of asking (ask only for destructive or out-of-worktree actions); implementers only on disjoint files; the register is read-only for page writers (deltas, `tools/claims_delta.py`); writers never run `--fix-tags`.
7. `## 7. Environment gotchas` — only the ones about this repository: the Bash cwd reset; heredoc apostrophes (long files through the Write tool); the CRLF survivors by name (`docs/progress.md`, `docs/decisions.md`, `docs/modding/patterns.md`, `docs/testing/README.md`, `tools/README.md` — check each with `file` before listing it); the stray client. The platform truths (`-debug` parks on an unguarded raise; the corpus drifts, so every count is dated) are one line each pointing at their rule on `platform/lessons.md`.
8. `## 8. Memory` — the memory file path and that it is updated at every close.
9. `## 9. Restructure status and resume point` — transitional, removed at the Phase 4 close: Phases 1, 2 and 3 closed (the ranges from today's § 3, one line each, no per-kind counts); Phase 4 next: write `docs/superpowers/plans/restructure-4-cut.md` with `superpowers:writing-plans` from the spec § Execution Phase 4 (the wall-map move with its `Ev`-cell rewrite from the `old section -> ids` map, `artifacts.md` moved whole with `Cited by` regenerated, the wiki-mirror contradiction table, the deletion of the old docs, ledgers and plans by pathspec in one commit, the acceptance run, every lint without `--partial`, the fresh-session skill test, the push); until then the old tree is readable, `docs/progress.md` and `docs/decisions.md` are frozen, and the spec at `docs/superpowers/specs/2026-09-17-reference-restructure-design.md` is the authority. The controller fills the Phase 3 range at the close (Task 15) — write the line with `<Phase 3 range>` as its placeholder text, the one placeholder this plan permits, and say so in the report.

Every path named exists at commit time (the same link check as Task 12, plus the paths in code spans: run `grep -o '`[^`]*`' CLAUDE.md` and check each that looks like a path). Gate: the narrative grep; `python tools/claims_check.py --staged` (nothing under its triggers — it says so); both doc_lint lines. Commit `CLAUDE.md: rewrite`.

### Task 15: Close (controller)

**Files:**
- Modify: `CLAUDE.md` § 9 (the Phase 3 range and the close commit); the memory file `C:\Users\Angus\.claude\projects\C--Users-Angus\memory\pz-nutrition-mod-project.md` and its `MEMORY.md` line; `docs/superpowers/plans/restructure-anchors.md` only if a delta moved or added an owner anchor (fold it in, so the plan stays the Phase 4 checklist).

- [ ] **Step 1: Gates**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_check.py --partial | tail -n 1 && python tools/claims_check.py | tail -n 1 && python -X utf8 tools/page_lint.py docs/areas/*.md docs/platform/*.md docs/facts/*.md docs/facts/other-mods/*.md docs/reference/datasets.md docs/reference/tools.md --partial | tail -n 1 && grep -rnP '\b(previously|corrected 20|resolved (in|by) slice|RESOLVED 20|CONTESTED|the review found|this slice)(?![A-Za-z])' docs/areas docs/platform docs/facts README.md STRATEGY.md CLAUDE.md | wc -l && grep -rn '\[T[0-9]' docs/areas docs/platform docs/facts docs/reference/datasets.md docs/reference/tools.md | wc -l && wc -l .claude/skills/*/SKILL.md | tail -n 11 && python tools/bus_inventory.py --check | tail -n 1 && python tools/doc_lint.py docs/mods-survey docs/modding | tail -n 1 && python tools/doc_lint.py docs/vanilla docs/modding docs/testing references docs/mods-survey/nutrition-mods.md | tail -n 1 && git diff --stat 74bb475..HEAD -- docs/vanilla docs/modding docs/mods-survey docs/testing docs/platform docs/facts testing data | tail -n 1 && python -m pytest tools/tests testing/tests -q 2>&1 | tail -n 1 && git status --short | wc -l && ls .superpowers/sdd/restructure-3-areas-skills-roots/*-delta.tsv 2>/dev/null | wc -l
```

Expected: `--partial` `0 findings, 0 warnings`; without `--partial` exactly the `reference/wall-map.md` owner findings (65 rows: count them and record the number — Phase 4 clears them); the page lint `0 findings` over 31 pages; both greps `0`; every skill ≤ 60 lines; `in sync`; both lints `0`; the old tree and the Phase 2 pages unchanged since `74bb475` except through `Register:` commits and controller corrections listed in the ledger (`git log --oneline 74bb475..HEAD -- docs/platform docs/facts` names only those); tests green (write the number down); a clean tree; every delta file listed was applied (each has its `Register: task N delta` commit).

- [ ] **Step 2: The skill-trigger proxy (acceptance 4)**

For each of the ten skills, dispatch one fresh Opus subagent with only: the ten `description` fields as a numbered list (extracted with the Task 13 gate's one-liner, names included), one task prompt written for that skill (a sentence an agent would receive — "add a vitamin-C store that survives a rejoin on our dedicated server" for `nutrition-new-nutrients`; "why does my weapon mod's `mod.info` load under `-nosteam` but not under Steam" for `pz-modding-platform`; "what does `Food.update` do at heat 1.2" for `pz-jar-research`; "run the mod under test against the fixture and read the reply" for `pz-mod-testing`; one each for the other six, in the ledger before dispatch), and the instruction to answer with the one skill name it would invoke and one sentence why. Save each answer to `.superpowers/sdd/restructure-3-areas-skills-roots/skill-trigger-<name>.md`. Ten of ten expected; a miss is a description to sharpen in one fix dispatch (Task 13's implementer resumed) and a re-run of that prompt. Record the tally in the ledger; the literal fresh-session test is Phase 4's.

- [ ] **Step 3: `CLAUDE.md` § 9, commit, push, memory**

Replace the `<Phase 3 range>` placeholder in `CLAUDE.md` § 9 with `` `<first commit>..<last commit>` `` (the plan's first commit to the last before the close) and add the close commit's name; then:

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_check.py --staged; git add CLAUDE.md && git commit -m "Restructure 3: close" -- CLAUDE.md && git push origin main && git log --oneline -1 && git status -sb | head -n 1
```

Then update the memory file's status paragraph (Phase 3 closed at the hash; 8 area pages, 2 reference pages, 10 skills, the roots; the register row count; NEXT = the Phase 4 plan `restructure-4-cut.md`) and the `MEMORY.md` index line; write `Task 15: complete` and `PLAN COMPLETE` in the ledger.

---

## What the whole-branch review checks

The final reviewer (Opus) reads the spec § The page contract (the options table, the writing rules, § Skills, § Coverage), § The target tree (the placement rule, the sync placement, the hard cases), § What the rewritten `CLAUDE.md` carries and § Acceptance items 1, 3, 4 and 8, then verifies on the branch (`74bb475..HEAD`):

1. Every `docs/areas/` page exists (8), lint-clean under `--partial`, within its cap, with the anchor plan's anchors in the contract's section order; `open-questions.md` indexes every `open` row (the lint's `open-index` clean) and tags its 44 owned rows at their `#x<n>` anchors; the two reference pages exist, tagged, lint-clean under the reference profile.
2. `python tools/claims_check.py --partial` → 0 findings; without `--partial` only the wall-map owner findings remain; rule 4 warnings under `docs/areas` at 0; `rules-dup` clean; rule 6 clean for all ten skills; every suffix canonical (a second `--fix-tags` changes nothing).
3. Twenty tagged sentences sampled across the area pages against their rows and the rows they cite: the reading says what the cited rows say and adds no number; every options table cites a row per line, marks nothing preferred, follows wall-map row order and ends with a question; every `## Rules` line is a byte-identical copy, an owned row or an applied `add` whose reason names the rows it rests on; no area page states a mechanism its owner page states (the hard cases: the per-key merge, the hook dispatch, the checksum gate, the registries, the packet mechanisms, the field contracts — cited, never restated).
4. The four folded experiments stand as walls on their pages in the spec's words (X4, X5, X13, X29), each linking its `open-questions.md#x<n>` line.
5. Every delta applied by a `Register: …` commit; no provisional tag left; the register's post block contiguous through the last minted id; `--register-only` clean; every `add` of kind `rule` carries a pointer copied from a row it rests on and a bound naming those rows.
6. The ten skills: ≤ 60 lines each, descriptions under 1,000 characters, `## Read first` pages exist, `## Rules quoted` lines byte-identical (rule 6), `pz-modding-platform` quotes § Coverage verbatim and excludes nutrition tasks; the trigger-proxy transcripts in the workspace, ten of ten.
7. `README.md`, `STRATEGY.md`, `CLAUDE.md`: every path resolves; no program history (no slice numbers, no phase letters except § 9's transitional lines, no dates but the build line); `CLAUDE.md` carries the spec's eight items in order and the router table; every rule today's `CLAUDE.md` carries is accounted for in Task 14's report (kept, moved, dropped with a reason); the memory file agrees with § 9.
8. Nothing changed under `docs/vanilla`, `docs/modding`, `docs/mods-survey`, `docs/testing`, `testing/`, `data/`; `docs/platform` and `docs/facts` changed only through `Register:` commits and ledgered controller corrections; the tools' tests green at the recorded count; the narrative grep empty over the three layers and the three roots.
