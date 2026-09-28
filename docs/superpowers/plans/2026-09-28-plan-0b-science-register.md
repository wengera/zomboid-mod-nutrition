# Plan 0b — Documentation pass: the science register Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the science register the spec's § 0 requires — every evidenced value the nutrition mod may ship, with its topic, grade, population and resolved citation — together with its library, checker, applier and page, and fill it from the eight science reports of the design phase so that Plans 3–5 cite a `settled` row for every number they ship and can find the rows a nutrient record needs by topic. The claims register is Plan 0a (`2026-09-28-plan-0a-claims-pass.md`); the two plans are independent in their registers, pages and tools, share five root files and the test count, and run one after the other, 0a first.

**Architecture:** One tool task first — `tools/sciencelib.py`, `tools/science_check.py`, `tools/science_delta.py`, their tests, the empty register, its page, its gate in `CLAUDE.md`. Then Wave S, fourteen harvest tasks in parallel, one per report or report section (45 to 95 graded rows each), each writing a part file with provisional ids that the controller validates and applies at the wave's close, with a re-scoped citation check that resolves every value the spec ships and a tenth of the rest. Then a roots task and the close. The binding procedure is `docs/superpowers/plans/2026-09-27-plan-0-page-procedure.md` Part B.

**Tech Stack:** Python 3.13 standard library (`tools/`, `pytest`), the TSV register `docs/reference/science.tsv`, Europe PMC (`https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:<doi>&format=json`) and Crossref (`https://api.crossref.org/works/<doi>`) for citation resolution.

**Spec:** `docs/superpowers/specs/2026-09-27-nutrition-mod-design.md` — § 0 (a number with no row does not ship), § 3 (the eight science reports and what the design takes from each), § 4.3–§ 4.5 and § 7 items 1–2, 9–12, 30–36 (the values the mod ships), § 9's last two bullets (the corrections to carry; the register's columns and checker). Two review rounds (`.superpowers/spec-review/plan-0/`) are folded here.

## Global Constraints

- **Order.** Plan 0a runs first and closes before this plan's Task 1 is dispatched; this plan's `CLAUDE.md`, `README.md`, `tools/README.md` and `docs/reference/tools.md` edits are made on the tree 0a left, and its pytest baseline is what `python -m pytest tools/tests testing/tests -q` reports at this plan's first commit (the ledger's first line records it); the count never drops, and Task 1 expects that baseline plus its own test count.
- **The register is read-only for writers.** A science row is a part file the controller applies with `tools/science_delta.py` at the wave's close, in task order; a writer never edits `docs/reference/science.tsv` or `tools/sciencelib.py`.
- **A settled row is a resolved row.** Every `settled` row's citation carries `doi:`, `pmid:`, `url:` or `isbn:`; every row whose value spec § 4.3–§ 4.5 or § 7 items 1–2, 9–12, 30–36 ships was resolved through Europe PMC or Crossref by the task that wrote it (title, first author and year matched), as was every tenth row of the part file and every row the report itself marks unverified; a citation that does not resolve is fixed from the record or the row goes `unverified` with the reason in `population`. The reports resolved every citation they carry through Europe PMC before quoting a number, which is why the tenth suffices for the rest and the reviewer's sample of ten is the audit.
- **A game choice is not a row.** A saturation constant, a clamp, a cadence, a dial's default or any number a report labels `GAME` or `INF` in its `## Proposed model` or `## Engine mapping` sections is design and mints nothing; where the report grounds it in a cited value, the cited value is the row.
- **The grade is the report's,** mapped once: `MA`, `RCT`, `COH`, `AUTH`, `TXT` stand; `EXP` (a controlled human depletion or dosing experiment that is not randomised) and `MODEL` (a published mathematical model cited for its shape and fitted constants, never for an effect size) are grades of their own; `CASE` maps to `COH`; a slashed pair (`MA/TXT`, `AUTH/COH`, `TXT/AUTH`, …) takes the left-most member of `sciencelib.RANK = ("MA", "RCT", "EXP", "COH", "AUTH", "TXT")` whichever order it is written in, and `MODEL` never appears in a pair (a model cited beside a trial is two rows); an `open` row carries no grade, because nothing was graded; `INF` and `GAME` are not rows.
- **Every row that is not open has a topic** from the controlled vocabulary `sciencelib.TOPICS`, so a later plan finds the rows a nutrient record or a system model needs with one filter. A slug the vocabulary lacks is **requested in the task's report**, never added by the task: the controller adds it to `sciencelib.TOPICS`, its test and `science.md` at the wave close, in the commit that lands the rows, and re-runs `--part` on the file before applying it.
- **Every report's `## Gaps` section is owned** by the task that owns that report's last evidence section, and every gap that names a missing quantity is an `open` row.
- **The citation cell is rewritten to the colon form.** Every report writes `PMID <digits>`; four (`science-vitamins.md`, `wave2-science-fatigue-sleep.md`, `wave2-science-healing-immunity-thermal.md`, `wave2-science-cognition-mood-perception.md`) also write `DOI 10.…`. Every task scripts `PMID ` → `pmid:` over its sections once; those four also script `DOI ` → `doi:`; a bare `PMC…` is dropped. `CITATION_RX` requires the colon prefix, so an unrewritten cell fails the checker.
- **Two irreconcilable sources are two `settled` rows** whose `parameter` names the disagreement; the design's choice between them is a ruling, not a row (the dehydration thresholds of spec § 7 item 11 are the case).
- **Nothing is ever deleted.** A row withdrawn after minting keeps its id and goes `unverified`, or `superseded` with its successor; contiguity is a minting invariant, not a repair path.
- **Provenance.** A row's `source` names the report section it came from under `docs/superpowers/research/`; the reports stay for the mod program's duration, and the tag `design-phase-v1` is created at the close of whichever of Plan 0a and Plan 0b closes second (Task 17 Step 4), so the sources stay readable after the program's own close removes them; a row is self-sufficient — its citation is the record and its source is history.
- **Gates.** Before every tool commit: `python -m pytest tools/tests testing/tests -q` green. Before every commit touching `docs/reference/science.tsv`: `python tools/science_check.py` → 0 findings. Before every commit touching `docs/` or `.claude/`: `python tools/claims_check.py --staged` → 0 (the science page and the tools page carry no register tags with numbers, so no provisional flags are needed here). `python tools/page_lint.py docs/reference/tools.md` → 0 when it changes. `science_check --scan` is given the mod's tree only, never `tools/` or `docs/`, which carry the reserved `S0000` in prose.
- **Commits:** pathspec, succinct subjects, no Claude attribution, never `--amend`, no push (the controller pushes at the close); every implementer and reviewer a fresh Opus subagent; harvest tasks commit nothing — the controller applies their part files. Per task, CLAUDE.md § 6's loop holds: amendments → implementer → report → review → fix rounds → `Task N: complete`. A ruling, ledgered: a gate line or a router row lands with the tool or page it serves, by the implementer, and the controller reviews it (Tasks 1 and 16); CLAUDE.md § 3's count line is written only at the close, from a fresh `pytest` run.
- **Briefs.** `task-brief` extracts one `### Task N` block, so every harvest task's step line names the procedure file and Part B, and the controller writes `.superpowers/sdd/2026-09-28-plan-0b-science-register/science-dispatch-common.md` at workspace creation — the procedure path, § Global Constraints in full, the grade mapping and rank, the citation rewrite, the topic vocabulary, the part-file path, the digest paragraph and the return contract — and names it in every amendments file.
- **Environment.** The Bash tool's cwd resets between calls (`cd /c/Users/Angus/repos/project_zomboid` first); Windows Python takes `C:/Users/...` paths; long files and any text with apostrophes go through the Write tool; `docs/reference/**` and `.claude/**` are pinned LF; `tools/README.md` is a CRLF survivor and is edited preserving its endings; `PYTHONIOENCODING=utf-8` when a checker's output is piped.
- **Angus's ruling, requested before Wave S is dispatched:** the spec's § 5 row names the three wave-1 science reports; this plan distils the five wave-2 reports too (Tasks 10–15), because Plans 3–5 ship their numbers and § 0 says a number with no row does not ship. If he strikes them, Tasks 10–15 are skipped and the science page's § Sources says so.

## Execution order

Task 1 (serial) → **Wave S**: Tasks 2–15 in parallel, at most six live at a time → **Wave S close** (controller: for each task in task order, `python tools/science_check.py --part <file>` → 0 — adding any requested slug to `sciencelib.TOPICS`, its test and `science.md` first — then `python tools/science_delta.py apply <file>`, recording the printed id map in the ledger; paste each task's digest paragraph into `docs/reference/science.md` § Sources; `python tools/science_check.py` → 0; `python -m pytest tools/tests -q` green if `sciencelib.py` changed; one commit `Science: wave S rows and digests`; one fresh reviewer reads the register for cross-task duplicates — the same citation and parameter minted twice — folded as `status` calls in a second commit) → Task 16 → Task 17 (the close).

## File structure

| path | responsibility | task |
|---|---|---|
| `tools/sciencelib.py`, `tools/science_check.py`, `tools/science_delta.py`, `tools/tests/test_sciencelib.py`, `tools/tests/test_science_check.py`, `tools/tests/test_science_delta.py`, `docs/reference/science.tsv` (header only), `docs/reference/science.md`, `tools/README.md`, `docs/reference/tools.md`, `CLAUDE.md` § 3 and § 4 | the register: schema, checker, applier, page, gate | 1 |
| `.superpowers/sdd/2026-09-28-plan-0b-science-register/task-N-science.tsv` (gitignored) → `docs/reference/science.tsv`, `docs/reference/science.md` § Sources | the fourteen harvests | 2–15 |
| `README.md`, `CLAUDE.md` § 1, `docs/reference/science.md` § Sources | the roots | 16 |
| `CLAUDE.md` § 3 count line, the tag `design-phase-v1`, the memory file | the close | 17 |

---

### Task 1: The science register — `sciencelib.py`, `science_check.py`, `science_delta.py`, the register, its page and its gate

**Files:**
- Create: `tools/sciencelib.py`, `tools/science_check.py`, `tools/science_delta.py`, `tools/tests/test_sciencelib.py`, `tools/tests/test_science_check.py`, `tools/tests/test_science_delta.py`, `docs/reference/science.tsv` (header line only), `docs/reference/science.md`
- Modify: `tools/README.md` § Reference tooling (three entries; CRLF preserved), `docs/reference/tools.md` (a new `## The science tools` section after § The claims tools with its `<a id="science-tools"></a>` anchor; the science register named in the stamp's scope line), `CLAUDE.md` § 3 (one gate line) and § 4 (one numbered rule) — the ruling above.

**Interfaces:**
- Produces:
  - `sciencelib.COLUMNS = ("id", "topic", "parameter", "value", "range", "population", "grade", "citation", "source", "status", "successor")`; `GRADES = ("MA", "RCT", "COH", "EXP", "MODEL", "AUTH", "TXT")`; `RANK = ("MA", "RCT", "EXP", "COH", "AUTH", "TXT")`; `STATUSES = ("settled", "open", "superseded", "unverified")`; `TOPICS`, the controlled vocabulary below; `ID_RX` (`^S\d{4}$`), `PROVISIONAL_RX` (`^S\d+\.\d+$`), `TOKEN_RX` (`\bS\d{4}\b`), `CITATION_RX` (a cell carries `doi:10.…`, `pmid:<digits>`, `url:http…` or `isbn:…`, case-insensitive prefixes, each preceded by the cell start, a space, `;`, `,` or `(`), `SOURCE_RX` (`^\S+\.md § .+$`, one space either side of `§`); `read_register(path) -> [dict]`, `write_register(path, rows)` (raising `RegisterError` on a cell holding a tab, a carriage return or a newline), `validate_row(row, provisional=False) -> [str]` (an `open` row may have an empty `grade`, `topic`, `value`, `range` and `citation`), `id_int`, `id_str`, `RegisterError`.
  - `TOPICS = ("vitamin-a", "vitamin-d", "vitamin-e", "vitamin-k", "vitamin-c", "thiamine", "riboflavin", "niacin", "pantothenate", "vitamin-b6", "biotin", "folate", "vitamin-b12", "choline", "sodium", "potassium", "chloride", "calcium", "magnesium", "phosphorus", "iron", "zinc", "copper", "iodine", "selenium", "manganese", "water", "fibre", "essential-fats", "carbohydrate-quality", "alcohol", "caffeine", "phytate", "sweat", "digestion", "energy", "body-composition", "lean-mass", "strength", "aerobic-capacity", "glycogen", "protein", "fatigue-sleep", "cognition", "mood", "perception", "healing", "immunity", "thermal", "toxicity", "starvation", "refeeding", "general")` — `digestion` for the gastric-emptying and absorption rows of § 7 item 1 and § 4.2, `general` for a cross-cutting row that fits no other; a slug the vocabulary lacks is requested in a task's report and added by the controller at the wave close.
  - `python tools/science_check.py [--register TSV] [--part TSV] [--scan PATH ...] [--staged] [--root DIR]` prints one `path:line: rule: detail` line per finding and exits 1 on any; rules `schema` (header, cell count, id form, contiguity from `S0001`, duplicates, topic in `TOPICS` and grade in `GRADES` on every row that is not open, status, value non-empty and citation form on a settled, unverified or superseded row, source form, successor present iff superseded and naming rows that exist and are not themselves superseded) and `scan` (every `S\d{4}` token in the named `.lua`, `.md`, `.py`, `.toml`, `.txt` files, the register itself and `docs/reference/science.md` excluded, names a row and names no superseded row). `--part` checks a part file with provisional ids and skips contiguity. `--staged` skips the run unless something staged is under the register or a `--scan` path.
  - `python tools/science_delta.py apply <part.tsv> [--register TSV] [--dry-run]` validates every row (a bad row aborts before anything is written, naming its line), mints the next free id for each in file order, appends, prints `S2.1 -> S0001` per row and `rows: N`; `python tools/science_delta.py status <Sdddd> <status> [--successor Sdddd] [--register TSV]` changes one row's status and successor, refusing a row already superseded.
  - `docs/reference/science.tsv`: the header line only; `docs/reference/science.md`: the page below, whose illustrative id is `S0000`, reserved and never minted.

- [ ] **Step 1: Write the failing tests**

`tools/tests/test_sciencelib.py`:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import sciencelib as sl
import pytest

GOOD = {"id": "S0001", "topic": "protein", "parameter": "protein intake at which fat-free-mass gains plateau", "value": "1.62 g/kg/day",
        "range": "95% CI 1.03-2.20", "population": "adults under resistance training, 49 studies n=1863", "grade": "MA",
        "citation": "Morton RW et al 2018, Br J Sports Med 52:376-384, doi:10.1136/bjsports-2017-097608, pmid:28698222",
        "source": "docs/superpowers/research/wave2-science-strength-training.md § 2", "status": "settled", "successor": ""}


def test_round_trip(tmp_path):
    p = tmp_path / "science.tsv"
    sl.write_register(str(p), [GOOD])
    assert p.read_text(encoding="utf-8").split("\n")[0] == "\t".join(sl.COLUMNS)
    assert sl.read_register(str(p)) == [GOOD]


def test_a_bad_header_raises(tmp_path):
    p = tmp_path / "science.tsv"
    p.write_text("id\tparameter\n", encoding="utf-8")
    with pytest.raises(sl.RegisterError):
        sl.read_register(str(p))


def test_a_cell_with_a_tab_or_newline_is_refused(tmp_path):
    p = tmp_path / "science.tsv"
    with pytest.raises(sl.RegisterError):
        sl.write_register(str(p), [dict(GOOD, citation="a\tb")])
    with pytest.raises(sl.RegisterError):
        sl.write_register(str(p), [dict(GOOD, parameter="a\nb")])


def test_validate_good_row():
    assert sl.validate_row(GOOD) == []


def test_validate_catches_each_field():
    assert any("id" in e for e in sl.validate_row(dict(GOOD, id="#0001")))
    assert sl.validate_row(dict(GOOD, id="S16.3"), provisional=True) == []
    assert any("topic" in e for e in sl.validate_row(dict(GOOD, topic="proteins")))
    assert any("grade" in e for e in sl.validate_row(dict(GOOD, grade="RCTs")))
    assert sl.validate_row(dict(GOOD, grade="MODEL")) == [] and sl.validate_row(dict(GOOD, grade="EXP")) == []
    assert any("status" in e for e in sl.validate_row(dict(GOOD, status="done")))
    assert any("citation" in e for e in sl.validate_row(dict(GOOD, citation="Morton 2018, Br J Sports Med")))
    assert any("value" in e for e in sl.validate_row(dict(GOOD, value="")))
    assert any("source" in e for e in sl.validate_row(dict(GOOD, source="somewhere")))
    assert any("source" in e for e in sl.validate_row(dict(GOOD, source="a.md §2")))
    assert any("successor" in e for e in sl.validate_row(dict(GOOD, status="superseded")))
    assert any("successor" in e for e in sl.validate_row(dict(GOOD, successor="S0002")))
    assert any("parameter" in e for e in sl.validate_row(dict(GOOD, parameter=" ")))


def test_an_open_row_may_be_empty_and_ungraded():
    assert sl.validate_row(dict(GOOD, value="", range="", citation="", grade="", topic="", status="open")) == []
    assert sl.validate_row(dict(GOOD, value="", range="", citation="", status="open")) == []
    assert any("grade" in e for e in sl.validate_row(dict(GOOD, grade="")))


def test_rank_resolves_a_slashed_pair():
    assert sl.resolve_grade("MA/TXT") == "MA" and sl.resolve_grade("TXT/AUTH") == "AUTH" and sl.resolve_grade("AUTH/COH") == "COH"
    assert sl.resolve_grade("CASE") == "COH" and sl.resolve_grade("RCT") == "RCT"
    with pytest.raises(ValueError):
        sl.resolve_grade("MODEL/RCT")
    with pytest.raises(ValueError):
        sl.resolve_grade("GAME")


def test_citation_forms():
    for c in ("doi:10.1/x", "PMID:12345", "pmid:12345 and doi:10.1/x", "(doi:10.1/x)", "url:https://lpi.oregonstate.edu/mic/vitamins/vitamin-A", "isbn:978-0-12-802928-2"):
        assert sl.CITATION_RX.search("Someone 2020, Journal, " + c), c
    assert not sl.CITATION_RX.search("Someone 2020, Journal, DOI 10.1/x")
    assert not sl.CITATION_RX.search("Someone 2020, Journal, PMID 12345")
```

`tools/tests/test_science_check.py`:

```python
import os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import sciencelib as sl
import science_check as sc

CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "science_check.py")
ROW = dict(id="S0001", topic="iron", parameter="p", value="1", range="", population="adults", grade="MA",
           citation="A 2020, J, doi:10.1/x", source="docs/superpowers/research/r.md § 1", status="settled", successor="")


def _tree(tmp_path, rows, files=None):
    root = tmp_path / "repo"
    (root / "docs" / "reference").mkdir(parents=True)
    sl.write_register(str(root / "docs" / "reference" / "science.tsv"), rows)
    for rel, text in (files or {}).items():
        p = root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8", newline="\n")
    return root


def _rules(findings):
    return sorted(f.rule for f in findings)


def test_clean_register_has_no_findings(tmp_path):
    root = _tree(tmp_path, [ROW, dict(ROW, id="S0002"), dict(ROW, id="S0003", topic="", grade="", value="", citation="", status="open")])
    assert sc.check(str(root)) == []


def test_schema_findings(tmp_path):
    rows = [ROW, dict(ROW, id="S0003"), dict(ROW, id="S0003", grade="X"), dict(ROW, id="S0004", topic="nope"),
            dict(ROW, id="S0005", status="superseded", successor="S0009")]
    root = _tree(tmp_path, rows)
    details = [f.detail for f in sc.check(str(root))]
    assert any("contiguous" in d for d in details)
    assert any("duplicate" in d for d in details)
    assert any("grade" in d for d in details)
    assert any("topic" in d for d in details)
    assert any("successor S0009" in d for d in details)


def test_scan_resolves_tokens_and_skips_the_register_and_its_page(tmp_path):
    rows = [ROW, dict(ROW, id="S0002", status="superseded", successor="S0003"), dict(ROW, id="S0003")]
    root = _tree(tmp_path, rows, {"mod/a.lua": "local x = 1.62 -- S0001\nlocal y = 2 -- S0002\nlocal z = 3 -- S0042\n",
                                  "docs/reference/science.md": "the mod cites the bare id, `S0000`\n"})
    f = sc.check(str(root), scan=[str(root / "mod"), str(root / "docs")])
    assert _rules(f) == ["scan", "scan"]
    assert any("S0042" in x.detail for x in f) and any("S0002" in x.detail and "superseded" in x.detail for x in f)
    assert all(x.line in (2, 3) for x in f)


def test_part_mode_accepts_provisional_ids_and_skips_contiguity(tmp_path):
    part = tmp_path / "part.tsv"
    sl.write_register(str(part), [dict(ROW, id="S16.1"), dict(ROW, id="S16.7", citation="none")])
    f = sc.check_part(str(part))
    assert _rules(f) == ["schema"] and "citation" in f[0].detail and f[0].line == 3


def test_cli_exit_codes(tmp_path):
    root = _tree(tmp_path, [ROW])
    assert subprocess.run([sys.executable, CLI, "--root", str(root)], capture_output=True).returncode == 0
    root2 = _tree(tmp_path / "b", [dict(ROW, grade="nope")])
    r = subprocess.run([sys.executable, CLI, "--root", str(root2)], capture_output=True, text=True)
    assert r.returncode == 1 and "schema" in r.stdout
```

`tools/tests/test_science_delta.py`:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import sciencelib as sl
import science_delta as sd
import pytest

ROW = dict(id="S0001", topic="iron", parameter="p", value="1", range="", population="adults", grade="MA",
           citation="A 2020, J, doi:10.1/x", source="docs/superpowers/research/r.md § 1", status="settled", successor="")


def _register(tmp_path, rows):
    p = tmp_path / "science.tsv"; sl.write_register(str(p), rows); return str(p)


def _part(tmp_path, rows):
    p = tmp_path / "part.tsv"; sl.write_register(str(p), rows); return str(p)


def test_apply_mints_in_file_order(tmp_path):
    reg = _register(tmp_path, [ROW])
    part = _part(tmp_path, [dict(ROW, id="S16.1", parameter="a"), dict(ROW, id="S16.2", parameter="b")])
    changes = sd.apply(part, register=reg)
    assert changes == ["S16.1 -> S0002", "S16.2 -> S0003"]
    rows = sl.read_register(reg)
    assert [r["id"] for r in rows] == ["S0001", "S0002", "S0003"] and rows[2]["parameter"] == "b"


def test_apply_on_an_empty_register_starts_at_one(tmp_path):
    reg = _register(tmp_path, [])
    assert sd.apply(_part(tmp_path, [dict(ROW, id="S1.1")]), register=reg) == ["S1.1 -> S0001"]


def test_a_bad_row_aborts_before_any_write(tmp_path):
    reg = _register(tmp_path, [ROW])
    before = open(reg, encoding="utf-8").read()
    part = _part(tmp_path, [dict(ROW, id="S16.1"), dict(ROW, id="S16.2", grade="bad")])
    with pytest.raises(sd.DeltaError) as e:
        sd.apply(part, register=reg)
    assert "line 3" in str(e.value) and open(reg, encoding="utf-8").read() == before


def test_a_real_id_in_a_part_is_refused(tmp_path):
    reg = _register(tmp_path, [ROW])
    with pytest.raises(sd.DeltaError):
        sd.apply(_part(tmp_path, [dict(ROW, id="S0007")]), register=reg)


def test_status_supersedes_and_refuses_a_closed_lineage(tmp_path):
    reg = _register(tmp_path, [ROW, dict(ROW, id="S0002")])
    assert sd.status("S0001", "superseded", successor="S0002", register=reg) == "S0001 status -> superseded (successor S0002)"
    rows = {r["id"]: r for r in sl.read_register(reg)}
    assert rows["S0001"]["successor"] == "S0002"
    with pytest.raises(sd.DeltaError):
        sd.status("S0001", "open", register=reg)
    with pytest.raises(sd.DeltaError):
        sd.status("S0002", "superseded", register=reg)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tools/tests/test_sciencelib.py tools/tests/test_science_check.py tools/tests/test_science_delta.py -q`
Expected: collection errors — `ModuleNotFoundError: sciencelib`.

- [ ] **Step 3: Implement `tools/sciencelib.py`**

```python
#!/usr/bin/env python3
"""The science register: schema constants, TSV IO and the citation grammar.

Spec: docs/superpowers/specs/2026-09-27-nutrition-mod-design.md § 0 and § 9. A row is one evidenced
value the mod may ship: `id topic parameter value range population grade citation source status
successor`. `topic` is one slug of TOPICS, so the rows a nutrient record or a system model needs are
one filter away. The grades are the research reports' — MA (meta-analysis or systematic review), RCT,
COH (cohort or observational; a case report maps here), EXP (a controlled human depletion or dosing
experiment that is not randomised), MODEL (a published mathematical model cited for its shape and
fitted constants, never for an effect size), AUTH (an authority report such as a DRI or an EFSA
opinion), TXT (a narrative review, textbook or modelling paper); a slashed pair resolves to the
left-most member of RANK. A settled, unverified or superseded row names its record: a DOI or a
PubMed id for a paper, a URL for an authority page, an ISBN for a book. An open row is a named gap
and may be empty and ungraded. The mod cites a row by its bare id and `science_check.py --scan`
resolves every such token; the illustrative id on the register's page is S0000, reserved and never
minted."""
import re

COLUMNS = ("id", "topic", "parameter", "value", "range", "population", "grade", "citation", "source", "status", "successor")
GRADES = ("MA", "RCT", "COH", "EXP", "MODEL", "AUTH", "TXT")
RANK = ("MA", "RCT", "EXP", "COH", "AUTH", "TXT")
GRADE_ALIASES = {"CASE": "COH"}
STATUSES = ("settled", "open", "superseded", "unverified")
TOPICS = ("vitamin-a", "vitamin-d", "vitamin-e", "vitamin-k", "vitamin-c", "thiamine", "riboflavin", "niacin",
          "pantothenate", "vitamin-b6", "biotin", "folate", "vitamin-b12", "choline",
          "sodium", "potassium", "chloride", "calcium", "magnesium", "phosphorus", "iron", "zinc", "copper", "iodine",
          "selenium", "manganese", "water", "fibre", "essential-fats", "carbohydrate-quality",
          "alcohol", "caffeine", "phytate", "sweat", "digestion",
          "energy", "body-composition", "lean-mass", "strength", "aerobic-capacity", "glycogen", "protein",
          "fatigue-sleep", "cognition", "mood", "perception", "healing", "immunity", "thermal", "toxicity",
          "starvation", "refeeding", "general")
ID_RX = re.compile(r"^S\d{4}$")
PROVISIONAL_RX = re.compile(r"^S\d+\.\d+$")
TOKEN_RX = re.compile(r"\bS\d{4}\b")
CITATION_RX = re.compile(r"(?:^|[\s;,(])(?:doi:10\.\S+|pmid:\d+|url:https?://\S+|isbn:[\d-]+)", re.I)
SOURCE_RX = re.compile(r"^\S+\.md § .+$")
CITED_STATUSES = ("settled", "unverified", "superseded")
BAD_CELL_RX = re.compile(r"[\t\r\n]")


class RegisterError(Exception):
    pass


def id_int(s):
    return int(s[1:])


def id_str(n):
    return "S%04d" % n


def resolve_grade(token):
    """A report's grade token -> a GRADES member: an alias maps, a slashed pair takes the left-most member
    of RANK whichever order it is written in, MODEL never pairs, and a design label is not a grade."""
    parts = [GRADE_ALIASES.get(p.strip(), p.strip()) for p in token.split("/")]
    if any(p not in GRADES for p in parts):
        raise ValueError("%r is not a grade" % token)
    if len(parts) == 1:
        return parts[0]
    if "MODEL" in parts:
        raise ValueError("%r: MODEL never appears in a pair; a model beside a trial is two rows" % token)
    return min(parts, key=RANK.index)


def read_register(path):
    """Rows as dicts keyed by COLUMNS. Raises RegisterError on a bad header or a short row."""
    with open(path, encoding="utf-8", newline="") as f:
        lines = f.read().split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines or lines[0].rstrip("\r").split("\t") != list(COLUMNS):
        raise RegisterError("%s: header must be %s" % (path, "\t".join(COLUMNS)))
    rows = []
    for n, line in enumerate(lines[1:], 2):
        cells = line.rstrip("\r").split("\t")
        if len(cells) != len(COLUMNS):
            raise RegisterError("%s:%d: %d cells, expected %d" % (path, n, len(cells), len(COLUMNS)))
        rows.append(dict(zip(COLUMNS, cells)))
    return rows


def write_register(path, rows):
    for r in rows:
        for c in COLUMNS:
            if BAD_CELL_RX.search(r.get(c, "")):
                raise RegisterError("%s: cell %s holds a tab or a line break" % (r.get("id", "?"), c))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(COLUMNS) + "\n")
        for r in rows:
            f.write("\t".join(r.get(c, "") for c in COLUMNS) + "\n")


def validate_row(row, provisional=False):
    """Schema errors for one row (empty list = valid). Cross-row checks live in science_check."""
    errs = []
    rid = row.get("id", "")
    if not (ID_RX.match(rid) or (provisional and PROVISIONAL_RX.match(rid))):
        errs.append("id %r is not Sdddd%s" % (rid, " or S<task>.<n>" if provisional else ""))
    status = row.get("status")
    if status not in STATUSES:
        errs.append("status %r not in %s" % (status, STATUSES))
    if not row.get("parameter", "").strip():
        errs.append("parameter is empty")
    if status != "open":
        if row.get("topic") not in TOPICS:
            errs.append("topic %r not in TOPICS" % row.get("topic"))
        if row.get("grade") not in GRADES:
            errs.append("grade %r not in %s" % (row.get("grade"), GRADES))
    else:
        if row.get("topic") and row.get("topic") not in TOPICS:
            errs.append("topic %r not in TOPICS" % row.get("topic"))
        if row.get("grade") and row.get("grade") not in GRADES:
            errs.append("grade %r not in %s" % (row.get("grade"), GRADES))
    if status in CITED_STATUSES:
        if not row.get("value", "").strip():
            errs.append("value is empty on a %s row" % status)
        if not CITATION_RX.search(row.get("citation", "")):
            errs.append("citation carries no doi:, pmid:, url: or isbn: on a %s row" % status)
    if not SOURCE_RX.match(row.get("source", "")):
        errs.append("source %r is not <report>.md § <heading> (one space either side of the section sign)" % row.get("source", ""))
    succ = row.get("successor", "").strip()
    if status == "superseded" and not succ:
        errs.append("successor required when superseded")
    if status != "superseded" and succ:
        errs.append("successor set on a non-superseded row")
    if succ and not all(ID_RX.match(s.strip()) for s in succ.split(",")):
        errs.append("successor %r is not Sdddd[, Sdddd]" % succ)
    return errs
```

- [ ] **Step 4: Implement `tools/science_check.py`**

```python
#!/usr/bin/env python3
"""The science checker (spec § 9: the register's checker mirrors the claims checker's schema and pointer
rules and adds a citation-form rule).

Rules: schema (0: header, cell count, id form, contiguity from S0001, duplicate ids, topic and grade on
every row that is not open, status, a non-empty value and a doi:/pmid:/url:/isbn: citation on every
settled, unverified or superseded row, the source form, a successor present exactly when superseded and
naming rows that exist and are not themselves superseded) · scan (1: with --scan PATH…, every `S<dddd>`
token in the named .lua, .md, .py, .toml and .txt files names a row and names no superseded row; the
register itself and docs/reference/science.md, which carries the reserved S0000, are skipped — give
--scan the mod's tree, never tools/ or docs/). --part TSV checks one part file whose ids are provisional
and skips contiguity. --staged skips the run when nothing staged is under the register or a scanned path.
Exit 1 on any finding.

Usage: python tools/science_check.py [--register TSV] [--part TSV] [--scan PATH ...] [--staged] [--root DIR]"""
import argparse, collections, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sciencelib as sl

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = "docs/reference/science.tsv"
PAGE = "docs/reference/science.md"
SCAN_EXT = (".lua", ".md", ".py", ".toml", ".txt")
Finding = collections.namedtuple("Finding", "path line rule detail")


def _rel(path, root):
    return os.path.relpath(path, root).replace("\\", "/")


def _rows_with_lines(path):
    rows = sl.read_register(path)
    return list(zip(range(2, len(rows) + 2), rows))


def check_rows(rel, numbered, provisional=False):
    out, seen = [], {}
    for n, r in numbered:
        for e in sl.validate_row(r, provisional=provisional):
            out.append(Finding(rel, n, "schema", "%s: %s" % (r.get("id", "?"), e)))
        if r.get("id") in seen:
            out.append(Finding(rel, n, "schema", "%s: duplicate id (first at line %d)" % (r["id"], seen[r["id"]])))
        seen.setdefault(r.get("id"), n)
    if not provisional:
        expect = 1
        for n, r in numbered:
            if sl.ID_RX.match(r.get("id", "")):
                if sl.id_int(r["id"]) != expect:
                    out.append(Finding(rel, n, "schema", "%s: ids are contiguous from S0001, expected %s" % (r["id"], sl.id_str(expect))))
                expect = sl.id_int(r["id"]) + 1
        by = {r["id"]: r for _, r in numbered}
        for n, r in numbered:
            for s in [s.strip() for s in r.get("successor", "").split(",") if s.strip()]:
                if s not in by:
                    out.append(Finding(rel, n, "schema", "%s: successor %s is not in the register" % (r["id"], s)))
                elif by[s].get("status") == "superseded":
                    out.append(Finding(rel, n, "schema", "%s: successor %s is itself superseded" % (r["id"], s)))
    return out


def _scan_files(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
        else:
            for dp, _, fns in os.walk(p):
                for fn in sorted(fns):
                    if fn.endswith(SCAN_EXT):
                        yield os.path.join(dp, fn)


def check_scan(root, paths, rows):
    by = {r["id"]: r for r in rows}
    skip = {os.path.normcase(os.path.abspath(os.path.join(root, *REGISTER.split("/")))),
            os.path.normcase(os.path.abspath(os.path.join(root, *PAGE.split("/"))))}
    out = []
    for p in _scan_files(paths):
        if os.path.normcase(os.path.abspath(p)) in skip:
            continue
        with open(p, encoding="utf-8", errors="replace") as f:
            for n, line in enumerate(f, 1):
                for tok in sl.TOKEN_RX.findall(line):
                    if tok not in by:
                        out.append(Finding(_rel(p, root), n, "scan", "%s names no science row" % tok))
                    elif by[tok]["status"] == "superseded":
                        out.append(Finding(_rel(p, root), n, "scan", "%s is superseded by %s" % (tok, by[tok]["successor"])))
    return out


def check(root=REPO_ROOT, register=None, scan=None):
    path = register or os.path.join(root, *REGISTER.split("/"))
    rel = _rel(path, root)
    try:
        numbered = _rows_with_lines(path)
    except (sl.RegisterError, OSError) as e:
        return [Finding(rel, 1, "schema", str(e))]
    out = check_rows(rel, numbered)
    if scan:
        out += check_scan(root, scan, [r for _, r in numbered])
    return out


def check_part(path):
    try:
        numbered = _rows_with_lines(path)
    except (sl.RegisterError, OSError) as e:
        return [Finding(path, 1, "schema", str(e))]
    return check_rows(path.replace("\\", "/"), numbered, provisional=True)


def _staged_touches(root, paths):
    r = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=root, capture_output=True, text=True)
    staged = [l.strip().replace("\\", "/") for l in r.stdout.splitlines() if l.strip()]
    wanted = [REGISTER] + [_rel(p, root) for p in paths]
    return any(s == w or s.startswith(w.rstrip("/") + "/") for s in staged for w in wanted)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--register"); ap.add_argument("--part"); ap.add_argument("--scan", nargs="*", default=[])
    ap.add_argument("--staged", action="store_true"); ap.add_argument("--root", default=REPO_ROOT)
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    if a.staged and not _staged_touches(a.root, a.scan):
        print("science_check: nothing staged under %s or the scanned paths; skipped" % REGISTER)
        return 0
    findings = check_part(a.part) if a.part else check(a.root, a.register, a.scan)
    for f in findings:
        print("%s:%d: %s: %s" % (f.path, f.line, f.rule, f.detail))
    print("%d findings" % len(findings))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Implement `tools/science_delta.py`**

```python
#!/usr/bin/env python3
"""Apply a science task's part file to the science register, or change one row's status.

A part file has the register's header exactly; every row's id is provisional `S<task>.<n>`. `apply`
validates every row first (a bad row aborts before anything is written, naming its line), mints the
next free id for each in file order, appends them, and prints `S2.1 -> S0042` per row. `status`
changes one row's status and, when superseded, its successor; a row already superseded is refused,
so a lineage is never overwritten. Nothing is ever deleted.

Usage: python tools/science_delta.py apply <part.tsv> [--register TSV] [--dry-run]
       python tools/science_delta.py status <Sdddd> <status> [--successor Sdddd] [--register TSV]"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sciencelib as sl

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO_ROOT, "docs", "reference", "science.tsv")


class DeltaError(Exception):
    pass


def apply(part_path, register=REGISTER, dry_run=False):
    rows = sl.read_register(register)
    part = sl.read_register(part_path)
    nxt = max((sl.id_int(r["id"]) for r in rows), default=0) + 1
    changes, seen = [], set()
    for n, r in enumerate(part, 2):
        if not sl.PROVISIONAL_RX.match(r["id"]):
            raise DeltaError("%s line %d: id %r must be provisional S<task>.<n>" % (part_path, n, r["id"]))
        if r["id"] in seen:
            raise DeltaError("%s line %d: provisional id %s used twice" % (part_path, n, r["id"]))
        seen.add(r["id"])
        errs = sl.validate_row(r, provisional=True)
        if errs:
            raise DeltaError("%s line %d: %s" % (part_path, n, "; ".join(errs)))
    for r in part:
        new = dict(r); new["id"] = sl.id_str(nxt)
        changes.append("%s -> %s" % (r["id"], new["id"]))
        rows.append(new); nxt += 1
    if not dry_run:
        sl.write_register(register, rows)
    return changes


def status(rid, new_status, successor="", register=REGISTER):
    rows = sl.read_register(register)
    by = {r["id"]: r for r in rows}
    if rid not in by:
        raise DeltaError("status %s: no such row" % rid)
    row = by[rid]
    if row["status"] == "superseded":
        raise DeltaError("status %s: row is already superseded (successor %s)" % (rid, row["successor"]))
    row["status"] = new_status
    row["successor"] = successor if new_status == "superseded" else ""
    errs = sl.validate_row(row)
    if errs:
        raise DeltaError("status %s: %s" % (rid, "; ".join(errs)))
    if successor and successor not in by:
        raise DeltaError("status %s: successor %s is not in the register" % (rid, successor))
    sl.write_register(register, rows)
    return "%s status -> %s%s" % (rid, new_status, " (successor %s)" % successor if successor else "")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("apply"); a.add_argument("part"); a.add_argument("--register", default=REGISTER); a.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("status"); s.add_argument("id"); s.add_argument("status"); s.add_argument("--successor", default=""); s.add_argument("--register", default=REGISTER)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "apply":
            changes = apply(args.part, register=args.register, dry_run=args.dry_run)
            for c in changes:
                print(c)
            print("rows: %d%s" % (len(changes), " (dry run)" if args.dry_run else ""))
        else:
            print(status(args.id, args.status, successor=args.successor, register=args.register))
    except (DeltaError, sl.RegisterError, OSError) as e:
        print("error: %s" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run the tests**

Run: `python -m pytest tools/tests -q`
Expected: every new test passes; the total is the baseline plus the new count, none failing. Fix any mismatch between the tests and the code by changing the code.

- [ ] **Step 7: The register, its page, the docs and the gate**

Create `docs/reference/science.tsv` as exactly one line, the header `id	topic	parameter	value	range	population	grade	citation	source	status	successor` (tab-separated, LF). Run `python tools/science_check.py` → `0 findings`.

Create `docs/reference/science.md`:

```markdown
# The science register

The science register `docs/reference/science.tsv` holds every evidenced value the nutrition mod may ship: a requirement, a store size, an onset time, an effect size, a threshold, a rate, a fitted model constant. It is the second of the two registers the mod cites (spec § 0): the claims register says what the game does, the science register says what the evidence says, and a number in the mod with no row in either does not ship.

## Columns

| column | what it holds |
|---|---|
| `id` | `S` and four digits, contiguous from `S0001`; the mod cites the bare id (`S0000` is this page's illustration and is never minted) |
| `topic` | one slug of the controlled vocabulary below, so the rows a nutrient record or a system model needs are one filter away; empty on an open row |
| `parameter` | the quantity, as a noun phrase, with the direction of an effect where the row is an effect |
| `value` | the number and its unit, or the qualitative finding |
| `range` | the uncertainty or spread as the source gives it — a confidence interval, a study count, a between-study range |
| `population` | who was studied and in what context; every value is a central tendency for that population |
| `grade` | `MA`, `RCT`, `COH`, `EXP`, `MODEL`, `AUTH` or `TXT` (below); empty on an open row, because nothing was graded |
| `citation` | authors, year, journal, then the record: `doi:10.…`, `pmid:…`, `url:https://…` for an authority page, `isbn:…` for a book; two records separated by `; ` |
| `source` | the research report and section the row was harvested from, readable at the tag `design-phase-v1` |
| `status` | `settled`, `open` (a named gap: topic, grade, value and citation may be empty), `unverified` (a number quoted but not resolved), `superseded` |
| `successor` | the row that replaces a superseded one |

## Topics

Nutrients: `vitamin-a`, `vitamin-d`, `vitamin-e`, `vitamin-k`, `vitamin-c`, `thiamine`, `riboflavin`, `niacin`, `pantothenate`, `vitamin-b6`, `biotin`, `folate`, `vitamin-b12`, `choline`, `sodium`, `potassium`, `chloride`, `calcium`, `magnesium`, `phosphorus`, `iron`, `zinc`, `copper`, `iodine`, `selenium`, `manganese`, `water`, `fibre`, `essential-fats`, `carbohydrate-quality`, `alcohol`, `caffeine`, `phytate`, `sweat`, `digestion`. Systems: `energy`, `body-composition`, `lean-mass`, `strength`, `aerobic-capacity`, `glycogen`, `protein`, `fatigue-sleep`, `cognition`, `mood`, `perception`, `healing`, `immunity`, `thermal`, `toxicity`, `starvation`, `refeeding`. `general` is for a cross-cutting row that fits no other. The vocabulary is `sciencelib.TOPICS`; a slug is requested in a harvest task's report and added by the controller in the commit that lands the rows, with the reason.

## Grades

| grade | meaning |
|---|---|
| `MA` | a meta-analysis, network meta-analysis, meta-regression or systematic review |
| `RCT` | a randomised controlled trial, a controlled crossover or an inpatient controlled trial |
| `EXP` | a controlled human depletion or dosing experiment that is not randomised |
| `COH` | a cohort, an observational or cross-sectional study, a regression derived from one, or a case report |
| `AUTH` | an authority report — a DRI, an EFSA opinion, a position stand, a consensus statement |
| `TXT` | a narrative review, a textbook chapter, an editorial or a modelling paper |
| `MODEL` | a published mathematical model cited for its shape and fitted constants, never for an effect size |

A row's grade is the source's, never the row's importance. A source graded with a slashed pair takes the left-most member of the rank `MA`, `RCT`, `EXP`, `COH`, `AUTH`, `TXT`, whichever order it is written in; `MODEL` never appears in a pair, because a model cited beside a trial is two rows. Where a meta-analysis and a later update disagree, the row carries the later reading and both records. Two irreconcilable sources are two `settled` rows whose `parameter` names the disagreement; the design's choice between them is a ruling, not a row.

## Rules

- A value the mod ships rests on a `settled` row; an `open` or `unverified` row names what is missing and ships nothing.
- Every `settled` row's citation was resolved against its record through Europe PMC or Crossref before the row was minted: title, first author and year matched.
- A game choice — a saturation constant, a clamp, a cadence, a dial's default — is not a row; the row is the cited value the choice rests on, and the choice is named as one where it is made.
- `python tools/science_check.py` checks the register's schema before every commit that touches it; `python tools/science_check.py --scan <the mod's tree>` resolves every `S` id token the mod carries and fails a token that names no row or a superseded one; the scan is never given `tools/` or `docs/`, which carry the reserved illustration in prose.
- A row is minted by the controller from a task's part file with `python tools/science_delta.py apply <part.tsv>`; a writer never edits the register.
- A superseded row keeps its id and names its successor; a row withdrawn after minting goes `unverified` or `superseded`, never deleted; contiguity is a minting invariant, not a repair path.
- A row is self-sufficient: its citation is the record, and its source is provenance.

## Sources

The rows were distilled from the eight science reports of the design phase (2026-09-27), each of which resolved every citation it carried through Europe PMC and matched title, authors, journal and year before quoting a number. One paragraph per report follows as its rows land.
```

In `tools/README.md` § Reference tooling (CRLF preserved) add three entries in the file's shape (`sciencelib.py` — no CLI, the schema, the topic vocabulary, the grade rank; `science_check.py` — the command line above, its two rules, `--part`, `--staged`, exit codes; `science_delta.py` — `apply` and `status`, what each prints and refuses). In `docs/reference/tools.md`, after § The claims tools and its `### The register grammar`, add:

```markdown
<a id="science-tools"></a>
## The science tools

The science tools keep the science register `docs/reference/science.tsv` consistent and let the mod's own files be checked against it; the register's columns, topics, grades and rules are stated on [its page](science.md).

- `sciencelib.py` has no command line: it holds the science register's schema — its columns, topics, grades and their rank, and statuses — its TSV reader and writer, the row validator, the grade resolver, and the id, token and citation grammars, and it runs inside the checker and the applier.
- `science_check.py` reads the register and writes nothing: its `schema` rule checks the header, the cell count, the id form and contiguity, duplicates, the topic and grade vocabularies on every row that is not open, the status vocabulary, the value and the citation form on every row that is not open, the source form and the successor lineage, and its `scan` rule, under `--scan`, resolves every `S` id token in the named files against the register and fails a token with no row or a superseded one; `--part` checks a task's part file with provisional ids; `--staged` skips the run when nothing relevant is staged.
- `science_delta.py` is the controller's tool: `apply <part.tsv>` validates every row of a part file before writing anything, mints the next free id for each in file order and appends them; `status <id> <status> [--successor <id>]` changes one row's status and refuses a row already superseded.
```

Add `the science register` to the stamp's scope line of `docs/reference/tools.md`. In `CLAUDE.md` § 3 add after the `claims_check.py` line: "- `python tools/science_check.py --staged` → 0 findings before every commit that touches `docs/reference/science.tsv` (it says so and skips otherwise); the mod plans add `--scan <the mod's tree>` to it, never `tools/` or `docs/`." In `CLAUDE.md` § 4 add item 8: "**A science number:** a value the mod ships rests on a `settled` row of `docs/reference/science.tsv`; a writer files rows in a part file the controller applies with `tools/science_delta.py`, and every settled row's citation was resolved against its record before minting; the page is [reference/science](docs/reference/science.md)."

- [ ] **Step 8: Gates and commit**

Run: `python -m pytest tools/tests testing/tests -q` green; `python tools/page_lint.py docs/reference/tools.md` → 0; `python tools/science_check.py` → 0; stage everything and `python tools/claims_check.py --staged` → 0.

```bash
git add tools/sciencelib.py tools/science_check.py tools/science_delta.py tools/tests/test_sciencelib.py tools/tests/test_science_check.py tools/tests/test_science_delta.py docs/reference/science.tsv docs/reference/science.md tools/README.md docs/reference/tools.md CLAUDE.md
git commit -m "Science register: schema, checker, applier, page and gate" -- tools/sciencelib.py tools/science_check.py tools/science_delta.py tools/tests/test_sciencelib.py tools/tests/test_science_check.py tools/tests/test_science_delta.py docs/reference/science.tsv docs/reference/science.md tools/README.md docs/reference/tools.md CLAUDE.md
```

---

## Wave S — the harvests

Every task follows `docs/superpowers/plans/2026-09-27-plan-0-page-procedure.md` Part B and the dispatch-common file the controller names in the amendments. The steps, repeated in each task: (1) read Part B, the dispatch-common file and the report sections named; (2) script the citation rewrite over the sections (`PMID ` → `pmid:` on every report; `DOI ` → `doi:` on the four that need it; a bare `PMC…` dropped) and write the part file `.superpowers/sdd/2026-09-28-plan-0b-science-register/task-<N>-science.tsv` with provisional ids `S<N>.<n>`, resolving the citations § B3 names; (3) run `python tools/science_check.py --part <file>` until it prints `0 findings`; (4) write `task-<N>-report.md` as § B5 with a five-sentence digest paragraph of the sections for `science.md` § Sources (what they cover, the population caveat, the largest gap) and any slug the sections need that `TOPICS` lacks, and return the one-line count. No commit.

The rows the spec ships, which every task resolves without exception (the tenth rule applies to the rest): the values named in spec § 4.3 (energy and body), § 4.4 (kinetics), § 4.5 (effects) and § 7 items 1–2, 9–12, 30–36 for the task's topics. Each task's text names the spec's items for its sections. A report's `## Gaps` section belongs to the task that owns the report's last evidence section, and every gap that names a missing quantity is an `open` row.

### Task 2: `science-energy-body.md` → rows (about 90)

Sections 1–9 (resting expenditure, activity expenditure, body composition dynamics, protein and muscle, muscle memory, strength versus lean mass, hydration, starvation timeline, obesity and excess) and `## Gaps`; topics `energy`, `body-composition`, `lean-mass`, `strength`, `protein`, `water`, `starvation`, `refeeding`, `digestion`. Shipped values (resolve every one): the Mifflin–St Jeor lean-mass form, the 2024 Compendium METs the report quotes, Alpert's ceiling, the Forbes and Hall partitioning relations, the hypertrophy and loss rates, the hydration thresholds (both conflicting sources as two rows, spec § 7 item 11), the refeeding incidences (item 12). Correction to carry (spec § 9): the dehydration-and-strength line is minted from Savoie 2015 (`−5.5` per cent strength, `−8.3` per cent muscular endurance) with the earlier citation beside it. The stomach-emptying constants of § 7 item 1 are `open` rows under `digestion`.

- [ ] Steps 1–4 as Part B of `docs/superpowers/plans/2026-09-27-plan-0-page-procedure.md`.

### Task 3: `science-vitamins.md` → rows, the fat-soluble vitamins, the cross-cutting section and the gaps (about 90)

Sections `## Vitamin A`, `## Vitamin D`, `## Vitamin E`, `## Vitamin K`, `## Cross-cutting`, `### Cooking, canning and processing losses, consolidated` and `## Gaps`; topics `vitamin-a`, `vitamin-d`, `vitamin-e`, `vitamin-k`, `general` for a cross-cutting row, else the vitamin's own slug. Shipped values: the requirements, store sizes, onset timelines and deficiency and excess thresholds spec § 4.4 names for these four; the vitamin A dark-adaptation rows § 4.5 leans on; the vitamin K bleeding finding (not defensible) beside Task 15's; the processing-loss factors Plan 6's item pass uses. Correction to carry: the vitamin D respiratory-infection effect is minted from Jolliffe 2025 with Martineau 2017 beside it and the value Jolliffe gives (this task mints the requirement, store and status rows; Task 15 the effect-size row; the controller's whole-wave read folds a duplicate). The `DOI ` rewrite applies.

- [ ] Steps 1–4 as Part B of `docs/superpowers/plans/2026-09-27-plan-0-page-procedure.md`.

### Task 4: `science-vitamins.md` → rows, vitamin C and the first B vitamins (about 75)

Sections `## Vitamin C`, `## Vitamin B1 (thiamine)`, `## Vitamin B2 (riboflavin)`, `## Vitamin B3 (niacin)`, `## Vitamin B5 (pantothenic acid)`; topics `vitamin-c`, `thiamine`, `riboflavin`, `niacin`, `pantothenate`. Shipped values: the requirements, stores and onsets § 4.4 names; vitamin C and colds in exerting cold-exposed populations (§ 4.5). The `DOI ` rewrite applies.

- [ ] Steps 1–4 as Part B of `docs/superpowers/plans/2026-09-27-plan-0-page-procedure.md`.

### Task 5: `science-vitamins.md` → rows, the remaining B vitamins and choline (about 80)

Sections `## Vitamin B6`, `## Vitamin B7 (biotin)`, `## Vitamin B9 (folate)`, `## Vitamin B12`, `## Choline`; topics `vitamin-b6`, `biotin`, `folate`, `vitamin-b12`, `choline`. Shipped values: the requirements, stores and onsets § 4.4 names; B12 at real scale (§ 7 item 10); the two-compartment B12 model's constants (item 9). The `DOI ` rewrite applies.

- [ ] Steps 1–4 as Part B of `docs/superpowers/plans/2026-09-27-plan-0-page-procedure.md`.

### Task 6: `science-minerals-fibre-fats.md` → rows, the major minerals and chloride (about 45)

The sodium, potassium, chloride, calcium, magnesium and phosphorus sections; topics `sodium`, `potassium`, `chloride`, `calcium`, `magnesium`, `phosphorus`. Shipped values: the requirements, stores and onsets § 4.4 names; the electrolyte rows § 4.4's water-and-electrolytes model uses.

- [ ] Steps 1–4 as Part B of `docs/superpowers/plans/2026-09-27-plan-0-page-procedure.md`.

### Task 7: `science-minerals-fibre-fats.md` → rows, the trace minerals (about 50)

The iron, zinc, iodine, selenium, copper and manganese sections (the report has no chromium section); topics `iron`, `zinc`, `iodine`, `selenium`, `copper`, `manganese`. Shipped values: iron's two-compartment model constants (§ 7 item 9), iron's anaemic-grade thermal and fatigue rows (§ 4.5), the zinc gate (§ 7 item 33), the iodine gap as an `open` row.

- [ ] Steps 1–4 as Part B of `docs/superpowers/plans/2026-09-27-plan-0-page-procedure.md`.

### Task 8: `science-minerals-fibre-fats.md` → rows, fibre, fats, carbohydrate quality, sweat, alcohol, caffeine and phytate (about 55)

The fibre, the two fatty-acid, the carbohydrate-quality, the very-low-carbohydrate, the sweat, the alcohol, the caffeine and the phytate sections; topics `fibre`, `essential-fats`, `carbohydrate-quality`, `sweat`, `alcohol`, `caffeine`, `phytate`. Shipped values: the sweat-loss rows § 4.4 uses; phytate as the shared absorption property; alcohol and caffeine's requirement-side rows (their pharmacokinetics are Task 13's).

- [ ] Steps 1–4 as Part B of `docs/superpowers/plans/2026-09-27-plan-0-page-procedure.md`.

### Task 9: `science-minerals-fibre-fats.md` → rows, the cross-cutting section and the gaps (about 45)

Sections `## Cross-cutting` and `## Gaps`; topics `general` for a row that spans minerals, else the mineral's own slug; every gap naming a missing quantity an `open` row.

- [ ] Steps 1–4 as Part B of `docs/superpowers/plans/2026-09-27-plan-0-page-procedure.md`.

### Task 10: `wave2-science-strength-training.md` → rows (about 60)

Sections 1–6 (training dose, protein and energy, detraining and retraining, acute nutrition, micronutrients, strength versus lean mass) and `## Gaps`; topics `strength`, `lean-mass`, `protein`, `energy`. Section 7 and `## Proposed model` mint nothing (`INF` and `GAME`); where the model grounds a constant in a cited value, the cited value is the row. Shipped values (§ 4.3, § 7 items 7, 30): the Hubal responder distribution, the `1.6 g/kg/day` protein plateau, the deficit-to-strength relations and their recovery time, the detraining and retraining time courses, the dehydration and sleep penalties, the neural-and-mass two-term evidence.

- [ ] Steps 1–4 as Part B of `docs/superpowers/plans/2026-09-27-plan-0-page-procedure.md`.

### Task 11: `wave2-science-endurance-fitness.md` → rows (about 75)

Every evidence section and `## Gaps`; topics `aerobic-capacity`, `glycogen`, `iron`, `water`, `energy`. Shipped values (§ 4.3, § 7 item 31): the aerobic-capacity gain and loss time constants and Hickson's maintenance findings, the carbohydrate and glycogen effects, iron's effects on adaptation, the hydration findings for a clamped-intensity task, fat as load. The proposed coefficients, exponents and bounds mint nothing.

- [ ] Steps 1–4 as Part B of `docs/superpowers/plans/2026-09-27-plan-0-page-procedure.md`.

### Task 12: `wave2-science-fatigue-sleep.md` → rows, the two-process model and sleep loss (about 60)

The sections on the two-process model and on sleep-loss impairment; topics `fatigue-sleep`, `cognition`. Shipped values (§ 4.4, § 4.5, § 7 items 32–33): the two-process model's constants as `MODEL` rows (the `18.2 h` and `4.2 h` time constants, the `0.12` amplitude, the thresholds), the impairment findings behind the `24` hours awake to `0.05` per cent equivalence. The circadian phase choice and the `0.30` conversion mint nothing. The `DOI ` rewrite applies.

- [ ] Steps 1–4 as Part B of `docs/superpowers/plans/2026-09-27-plan-0-page-procedure.md`.

### Task 13: `wave2-science-fatigue-sleep.md` → rows, the nutritional, hydration, caffeine and alcohol determinants, and the gaps (about 60)

The remaining sections and `## Gaps`; topics `fatigue-sleep`, `iron`, `water`, `energy`, `caffeine`, `alcohol`. Shipped values: the iron-without-anaemia, mild-dehydration and energy-availability fatigue effects; caffeine's pharmacokinetics and tolerance course; alcohol's recovery effects; exercise timing. The `DOI ` rewrite applies.

- [ ] Steps 1–4 as Part B of `docs/superpowers/plans/2026-09-27-plan-0-page-procedure.md`.

### Task 14: `wave2-science-cognition-mood-perception.md` → rows (about 75)

Sections 1–4, § 5.6's sixteen unsupported mechanics and `## Gaps`; topics `cognition`, `mood`, `perception`, `vitamin-a`, `fatigue-sleep`. Shipped values (§ 4.5, § 7 item 33): vitamin A and dark adaptation; the null acute-fasting cognition findings; blood glucose and reaction time; the sleep-loss and alcohol cross-calibration sources; the sixteen mechanics named unsupported — each a row whose value is the finding "no supported effect" with its citation, so a later plan cannot ship it by accident. The `DOI ` rewrite applies.

- [ ] Steps 1–4 as Part B of `docs/superpowers/plans/2026-09-27-plan-0-page-procedure.md`.

### Task 15: `wave2-science-healing-immunity-thermal.md` → rows (about 95)

Sections 1–6 and `## Gaps`; topics `healing`, `immunity`, `thermal`, `toxicity`, `iron`, `water`, `vitamin-c`, `vitamin-d`, `vitamin-k`, `protein`. Shipped values (§ 4.5, § 7 item 34): the healing and infection multipliers from protein-energy status; vitamin K and bleeding; the vitamin D respiratory-infection effect from Jolliffe 2025 (the effect-size row; Task 3 mints the requirement rows); vitamin C and colds; fracture healing; iron and dehydration in thermoregulation; the toxicity thresholds. `EXP` and `CASE` rows take their grades per the mapping. The `DOI ` rewrite applies.

- [ ] Steps 1–4 as Part B of `docs/superpowers/plans/2026-09-27-plan-0-page-procedure.md`.

### Task 16: The roots

**Files:** Modify `README.md` (§ Tags gains one line: a science row is cited by its bare id, checked by `science_check.py --scan`; the tree line for `docs/reference/` names the science register; the Reading order names `reference/science.md`), `CLAUDE.md` § 1 (the routing table gains "cite a nutrition-science value | reference/science → the register | —"; the first paragraph names the science register beside the claims register — the ruling above), `docs/reference/science.md` § Sources (the controller pasted the fourteen digests at the wave close; this task reads them once for voice and adds the closing sentence naming the tag `design-phase-v1`).

- [ ] Step 1 read the three files · Step 2 edit · Step 3 `python tools/claims_check.py --staged` → 0 · Step 4 commit `Roots: the science register in README and CLAUDE.md` · Step 5 report.

### Task 17: The close (controller)

- [ ] **Step 1: Whole-pass review.** One fresh Opus reviewer, read-only: the register against the spec — every value § 4.3–§ 4.5 and § 7 items 1–2, 9–12, 30–36 name is present and `settled`, listed in the review against the spec item it serves (this is what makes the register usable by Plans 3–5 rather than merely consistent); ten citations resolved live; the topics against the vocabulary; duplicates across tasks. Findings become one consolidated fix wave (fresh implementers writing `status` calls and small part files) and one scoped re-review.
- [ ] **Step 2: Gates.** `python tools/science_check.py` → 0; `python -m pytest tools/tests testing/tests -q` green and `CLAUDE.md` § 3's count line written from that run's total and today's date; `python tools/claims_check.py` (full) → 0; `python tools/page_lint.py docs/reference/tools.md` → 0.
- [ ] **Step 3: Record.** The memory file `C:\Users\Angus\.claude\projects\C--Users-Angus\memory\pz-nutrition-mod-project.md` and its `MEMORY.md` index (Plan 0b closed at `<commit>`; the row counts by status, grade and topic; Angus's ruling on the wave-2 rows; the resume point: Plan 1's writing-plans); the project memory pointer. The ledger's last line: `Plan 0b: complete`.
- [ ] **Step 4: Tag and push.** Plan 0a has closed, so `git tag design-phase-v1 HEAD && git push origin design-phase-v1` (if the tag exists, verify it contains `docs/superpowers/research/` and say so in the ledger). Then `git push origin main`. Nothing under `docs/superpowers/research/` is removed by this plan.

---

## Self-review (run by the controller before dispatch)

- **Spec coverage.** § 9's last bullet (the register: columns, grades, checker with a citation-form rule) → Task 1, with the `topic` column, the `EXP`/`MODEL` grades and the rank the reports need; § 9's science corrections → Tasks 2, 3, 15; § 5 row "the three science reports distilled into rows" → Tasks 2–9; the wave-2 reports → Tasks 10–15 (flagged for Angus); § 0 "a number with no row does not ship" → the shipped-value lists per task and the close's spec-item audit; every report's `## Gaps` → Tasks 2, 3, 9, 10, 11, 13, 14, 15.
- **Placeholder scan.** No "TBD", no "similar to"; each harvest task names its sections, topics, shipped values and corrections; the tool task carries its code and tests.
- **Type consistency.** `S<task>.<n>` is the provisional form Part B uses and `science_delta.apply` accepts; `TOPICS` in `sciencelib.py`, on `science.md` and in Part B are the same list (with `chloride` and `digestion`, without `chromium`); the grades in `GRADES`, the rank in `RANK`, on `science.md` and in Part B's mapping agree; `S0000` is the reserved illustration and `--scan` skips the page that carries it and is never given `tools/`.
