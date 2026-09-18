# Restructure Phase 0 + 1 — program close and the claims register — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the research program at the tag `research-program-v1`, then build the claims register (`docs/reference/claims.tsv`), its checker, the harness command generator and the moved reference files, so Phases 2–4 can write pages from register rows and prove coverage before the old tree is deleted.

**Architecture:** Three small Python tools in `tools/` share one library (`claimslib.py`: the register schema, the tag and pointer grammars, TSV IO). `claims_harvest.py` extracts candidate rows mechanically from the old docs and the do-not-cite tables; nine parallel harvest tasks turn candidates into register rows in per-group part files under disjoint id sub-blocks; `claims_harvest.py merge` folds the parts into one `claims.tsv` and one coverage file. `claims_check.py` enforces the schema now (`--register-only`) and the page rules from Phase 2 on. `bus_inventory.py` generates `docs/reference/harness-commands.md` from a structured comment block above every `TK.register` site (the one harness edit, comments only). No game boot except the acceptance run at the end.

**Tech Stack:** Python 3 (stdlib only: `re`, `csv`, `argparse`, `subprocess`, `json`, `os`), pytest under `tools/tests/`, Git Bash, the existing `pzt` runner for the one acceptance run.

**Spec:** `docs/superpowers/specs/2026-09-17-reference-restructure-design.md` (APPROVED 2026-09-17). The plan argues from it; a conflict between this plan and the spec resolves to the spec. Every harvest task also binds to `docs/superpowers/plans/restructure-1-harvest-procedure.md`.

## Global Constraints

- The game install `D:\SteamLibrary\steamapps\common\ProjectZomboid` and the workshop folder are **read-only, always**. One live game session at a time, program-wide; `python testing/pzt doctor` before any boot; never `-safemode`.
- No new measurements. The register mints no evidence: every row is a harvested claim from the current library with its grade and pointer.
- The only harness edit is the structured comment block (`-- @args`, `-- @reply`, `-- @purpose`) directly above every `TK.register("<name>", …)` site under `testing/PZTestKit/PZTestKit/42/media/lua/{shared,server,client}/`. No behaviour change. `python tools/luabalance.py <files>` green before that commit; it lands in its own commit before the acceptance run.
- Never edit artifacts under `testing/artifacts/`, drivers under `testing/experiments/*.py` (except the new `_template.py`), profiles, or the wiki mirrors.
- Register format: `docs/reference/claims.tsv`, tab-separated, no quoting, header `id	claim	grade	pointer	bound	status	successor	kind	source	owner`; ids `#0001`… never reused; sub-blocks: vanilla `#0001–#0800` (G1a `#0001–#0200`, G1b `#0201–#0450`, G1c `#0451–#0600`, G1d `#0601–#0800`), modding `#0801–#1300` (G2a `#0801–#1000`, G2b `#1001–#1120`, G2c `#1121–#1300`), survey `#1301–#1700` (G3a `#1301–#1550`, G3b `#1551–#1700`), testing/data/tools/ledgers `#1701–#2000` (G4), post-harvest `#2001+` minted by the controller alone. Within a sub-block, used ids are contiguous from its first id.
- `grade` ∈ `C M W` = the strongest grade among the row's pointers (`M` > `C` > `W`). `pointer` forms: `jar:` `run:` `wiki:` `lua:` `mod:` `repo:` `data:` `tool:` (`run:` is M, `wiki:` is W, the rest C); `lua:`, `mod:`, `repo:` carry quoted anchor text. `bound` first token ∈ `none`, `n=<int>`, `one-side`, `C-only`, `one-fixture`, `arith.`, `inference`, `uncommitted`, `snapshot`. `status` ∈ `settled open superseded unverified`; `successor` filled only when superseded. `kind` ∈ `mechanism order table count verdict rule bound contradiction tool open`. `owner` = `<areas|platform|facts|reference>/<page>.md#<anchor>`.
- Tag grammar: `[#0417]` for a settled C row with no bound; otherwise the canonical suffix `/<grade>[/<bound token>][/<status>]` — `[#0417/M]`, `[#0417/M/n=1]`, `[#0417/C/inference]`, `[#0417/C/open]`, `[#0417/M/uncommitted/unverified]`; several: `[#0417/M, #0512]`; provisional `[T<task>.<n>]`.
- `docs/reference/` files are outside the page contract; `tools/doc_lint.py` keeps running on the old dirs until the cut (gates: `python tools/doc_lint.py docs/mods-survey docs/modding` → 0; `python tools/doc_lint.py docs/vanilla docs/modding docs/testing references docs/mods-survey/nutrition-mods.md` → 0). `python -m pytest tools/tests testing/tests -q` green (283 before this plan; never let it drop).
- Commits: brief subject, **no Claude attribution**, **pathspec commits** (`git commit -m "…" -- <paths>`), **never `--amend`**, no push from a task (the controller pushes at the close; the Phase 0 tag push is the controller's).
- CRLF: `docs/progress.md`, `docs/decisions.md`, `docs/modding/patterns.md`, `docs/testing/README.md` are CRLF — read with `newline=''` and preserve; new files are LF. Check a Lua file's ending with `git ls-files --eol <path>` before editing it and preserve it.
- Environment: the Bash tool's cwd resets between calls — `cd /c/Users/Angus/repos/project_zomboid` in every call. Long heredocs with apostrophes fail — write files with the Write tool. `.superpowers/` is gitignored; nothing there is a deliverable except this plan's workspace notes.
- Subagents: Opus implementers and reviewers, always specified; the lead is Fable.

---

## File structure

| Path | Responsibility | Task |
|---|---|---|
| `CLAUDE.md` § 3, § 4, § 7 | status → program closed; resume point → this plan; `luabalance.py` path | 1, 2 |
| `tools/luabalance.py`, `tools/tests/test_luabalance.py` | the Lua bracket/`end` balance check, moved into the tree | 2 |
| `tools/claimslib.py`, `tools/tests/test_claimslib.py` | the register schema constants, TSV IO, pointer/bound/tag grammars, row validation | 3 |
| `tools/claims_harvest.py`, `tools/tests/test_claims_harvest.py` | `candidates` (evidence rows and graded paragraphs → TSV), `do-not-cite` (artifacts README → CSV), `merge` (parts → register + coverage) | 4 |
| `tools/bus_inventory.py`, `tools/tests/test_bus_inventory.py` | parse `TK.register` sites and their comment blocks → `docs/reference/harness-commands.md`; `--check` | 5 |
| `testing/PZTestKit/PZTestKit/42/media/lua/**/*.lua` (comments only), `docs/reference/harness-commands.md` | the 64 comment blocks; the generated table | 6 |
| `docs/reference/experiments.md`, `docs/reference/jar-method-notes.md`, `docs/reference/run-aliases.csv`, `testing/experiments/_template.py`, `tools/tests/test_template.py` | the moved working reads, the run alias table, the driver template | 7 |
| `docs/superpowers/plans/restructure-anchors.md` | the anchor plan (deliverable 0 of the harvest) | 8 |
| `tools/claims_check.py`, `tools/tests/test_claims_check.py` | rules 0–7, `--register-only`, `--partial`, `--staged`, `--allow-provisional`, `--fix-tags`, `--view`, `--section-map` | 9 |
| `docs/reference/do-not-cite.csv` | the do-not-cite keys, generated and hand-verified | 10 |
| `docs/reference/parts/claims-<group>.tsv`, `docs/reference/parts/coverage-<group>.md` | nine harvest parts (G1a, G1b, G1c, G1d, G2a, G2b, G2c, G3a, G3b, G4) | 11–20 |
| `docs/reference/claims.tsv`, `docs/reference/claims-coverage.md` | the merged register and coverage table; the anchor plan folded | 21 |
| `tools/README.md` | entries for the five new tools | 2, 3, 4, 5, 9 |
| (live) | the acceptance run | 22 |
| `CLAUDE.md` § 3, § 4 | the close | 23 |

Task order and parallelism: 1 → 2 → 3 → {4, 5, 7, 8, 9 in parallel: disjoint files} → 6 (needs 5) → 10 (needs 4) → 11–19 (need 3, 4, 7, 8, 9, 10; parallel on disjoint part files) → 20 (G4, after 15–17 are committed: it needs their ids as successors) → 21 → 22 → 23.

---

### Task 1: Close the research program and tag it (Phase 0)

**Files:**
- Modify: `CLAUDE.md` § 3 (lines 22–35) and § 4 (lines 36–41)
- Modify (gitignored, no commit): `.superpowers/sdd/14-feasibility-notes/progress.md`

**Interfaces:**
- Produces: the tag `research-program-v1` on the commit that carries the `CLAUDE.md` edit; the controller pushes the tag (`git push origin research-program-v1`) — a task never pushes.

- [ ] **Step 1: Record the ruling in the slice-14 ledger**

Append to `.superpowers/sdd/14-feasibility-notes/progress.md` (gitignored; Write tool):

```
- 2026-09-17: Ruling: slice 14 is CLOSED unrun — its six notes are superseded by docs/areas/ under the approved restructure spec (docs/superpowers/specs/2026-09-17-reference-restructure-design.md, commit 5845604) — cost if wrong: the area pages are written from the same briefs in Phase 3. The research program closes at tag research-program-v1 (Phase 0 of docs/superpowers/plans/restructure-1-register.md).
```

- [ ] **Step 2: Rewrite `CLAUDE.md` § 3 and § 4**

Read `CLAUDE.md` lines 22–41 first. Replace the body of `## 3. Status snapshot (2026-09-17)` with:

```markdown
Slices 01–13 are **done and pushed** (12 closed `f36a860..17a683b`, close `75e277c`; 13 closed `2019621..91fda27`, close `c3e60a0`). Slice 14 (feasibility notes) was **closed unrun**: its six design areas are written once as `docs/areas/` by the restructure. The research program is **closed at the tag `research-program-v1`** — everything the program produced (plans, specs, ledgers, the old doc tree) is reachable there forever.

The repo is now being restructured into an agent-facing reference under `docs/superpowers/specs/2026-09-17-reference-restructure-design.md` (APPROVED 2026-09-17). Four phases: 0 close (done at the tag) · 1 the claims register, checker and generator (`docs/superpowers/plans/restructure-1-register.md`) · 2 `platform/` + `facts/` pages · 3 `areas/` + skills + roots · 4 the cut. Until Phase 4 lands, the old tree (`docs/vanilla`, `docs/modding`, `docs/mods-survey`, `docs/testing`) remains the readable reference and `docs/progress.md` / `docs/decisions.md` are frozen — do not extend them; rulings go in the plan's SDD ledger.
```

Replace the body of `## 4. Resume point — do exactly this` with:

```markdown
1. Read the spec, then the plan in progress (`docs/superpowers/plans/restructure-1-register.md`; later plans are named `restructure-2-…`, `restructure-3-…`, `restructure-4-…`) and its SDD ledger `.superpowers/sdd/<plan-basename>/progress.md`.
2. Run the plan with `superpowers:subagent-driven-development` exactly as § 5 describes. Tasks with a `Task <N>: complete` line are done; resume at the first without one.
3. At each plan's close: run the gates in § 6, push, update this section and the memory file.
```

- [ ] **Step 3: Verify the file still passes the doc lint and the tests**

Run: `cd /c/Users/Angus/repos/project_zomboid && python tools/doc_lint.py docs/mods-survey docs/modding && python -m pytest tools/tests testing/tests -q 2>&1 | tail -2`
Expected: `0 findings` (or the lint's zero-count line) and `283 passed`.

- [ ] **Step 4: Commit and tag**

```bash
cd /c/Users/Angus/repos/project_zomboid
git commit -m "Program close: slice 14 folded into the restructure; resume point -> restructure plans" -- CLAUDE.md
git tag -a research-program-v1 -m "Research program v1: slices 01-13 done, 14 folded into the restructure; the pre-restructure tree"
git tag -l research-program-v1 && git log --oneline -1
```

Expected: the tag lists; HEAD is the close commit. Report the commit hash; the controller pushes `main` and the tag.

---

### Task 2: Move `luabalance.py` into the tree

**Files:**
- Create: `tools/luabalance.py` (from `.superpowers/sdd/_tools/luabalance.py`, byte-identical)
- Create: `tools/tests/test_luabalance.py`
- Modify: `tools/README.md` (a new `## Reference tooling` section before `## Planned (P4)`), `CLAUDE.md` § 7 (the balance-check path)

**Interfaces:**
- Produces: `tools/luabalance.py <lua files…>` prints one line per file and exits 0 iff every file is `BALANCED`; module function `report(path) -> (name, braces, parens, brackets, end_depth, neg_lines, verdict)`.

- [ ] **Step 1: Write the failing test**

`tools/tests/test_luabalance.py`:

```python
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import luabalance

CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "luabalance.py")

def _write(d, name, text):
    p = os.path.join(d, name); open(p, "w", encoding="utf-8").write(text); return p

def test_balanced_file_reports_balanced():
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "ok.lua", "-- a comment with an unmatched ( and a [[\nlocal t = { a = 1, s = \"}\" }\nfunction f(x) if x then return { } end end\n")
        assert luabalance.report(p)[6] == "BALANCED"

def test_missing_function_line_is_unbalanced():
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "bad.lua", "local x = 1\n  if x then return x end\nend\n")
        name, b, par, s, depth, neg, verdict = luabalance.report(p)
        assert verdict == "UNBALANCED" and depth == -1 and neg == 1

def test_cli_exit_code_follows_verdict():
    with tempfile.TemporaryDirectory() as d:
        ok = _write(d, "ok.lua", "function f() end\n")
        bad = _write(d, "bad.lua", "end\n")
        assert subprocess.run([sys.executable, CLI, ok], capture_output=True).returncode == 0
        assert subprocess.run([sys.executable, CLI, ok, bad], capture_output=True).returncode == 1
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd /c/Users/Angus/repos/project_zomboid && python -m pytest tools/tests/test_luabalance.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'luabalance'`.

- [ ] **Step 3: Copy the tool**

```bash
cd /c/Users/Angus/repos/project_zomboid && cp .superpowers/sdd/_tools/luabalance.py tools/luabalance.py && python tools/luabalance.py testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua
```

Expected: `PZTestKit_Core.lua  {} +0  () +0  [] +0   end-depth +0   neg-depth lines 0   BALANCED`.

- [ ] **Step 4: Run the test to see it pass**

Run: `python -m pytest tools/tests/test_luabalance.py -q` → `3 passed`.

- [ ] **Step 5: Document and re-point**

In `tools/README.md`, insert before `## Planned (P4)`:

```markdown
## Reference tooling

- `luabalance.py` — `python tools/luabalance.py <lua file> [...]`
  Bracket / block-`end` balance read-through for harness Lua (slice-08 shape, moved
  into the tree by the restructure). Strips comments and strings, then prints the
  delta of `{}` `()` `[]`, the `end`-depth and the count of lines where the depth
  went negative; exits 1 unless every file is `BALANCED`. Run it on every Lua file
  a harness commit touches, on the HEAD copy first and then the working tree.
```

In `CLAUDE.md` § 7 replace `python .superpowers/sdd/_tools/luabalance.py <lua files>` with `python tools/luabalance.py <lua files>`.

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git commit -m "tools: luabalance.py moved into the tree with tests" -- tools/luabalance.py tools/tests/test_luabalance.py tools/README.md CLAUDE.md
```

---

### Task 3: `claimslib.py` — the register schema and grammars

**Files:**
- Create: `tools/claimslib.py`
- Create: `tools/tests/test_claimslib.py`
- Modify: `tools/README.md` (`## Reference tooling`)

**Interfaces:**
- Produces (used by Tasks 4, 9 and every harvest task): the constants `COLUMNS`, `GRADES`, `STATUSES`, `KINDS`, `BOUND_TOKENS`, `POINTER_FORMS`, `LAYERS`, `BLOCKS`, `ID_RX`, `TAG_RX`, `PROVISIONAL_RX`, `OWNER_RX`; functions `read_register(path) -> list[dict]`, `write_register(path, rows)`, `parse_pointers(cell) -> list[(form, text)]`, `strongest_grade(forms) -> str`, `parse_bound(cell) -> (token, rest)`, `canonical_suffix(row) -> str`, `split_tag(inner) -> list[(id, suffix)]`, `iter_tags(text) -> iterator[(lineno, id, suffix)]`, `block_of(id_str) -> str`, `validate_row(row) -> list[str]`, `id_int(id_str) -> int`, `id_str(n) -> str`.

- [ ] **Step 1: Write the failing tests**

`tools/tests/test_claimslib.py`:

```python
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import claimslib as cl

ROW = {"id": "#0001", "claim": "Idle burn is 0.016 x weight/80 kcal per game-second.", "grade": "M",
       "pointer": "jar:Nutrition.updateCalories @295 L118; run:exp03-20260910-045523 body.json rows.r1_baseline",
       "bound": "n=1 server-side fit; idle branch only", "status": "settled", "successor": "",
       "kind": "mechanism", "source": "docs/vanilla/body-stats.md § Passive burn", "owner": "facts/body-and-weight.md#passive-burn"}

def test_roundtrip_tsv():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "claims.tsv")
        cl.write_register(p, [ROW])
        rows = cl.read_register(p)
        assert rows == [ROW]
        assert open(p, encoding="utf-8").read().splitlines()[0] == "\t".join(cl.COLUMNS)

def test_bad_header_raises():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.tsv"); open(p, "w").write("id\tclaim\n#0001\tx\n")
        try:
            cl.read_register(p); assert False, "expected RegisterError"
        except cl.RegisterError:
            pass

def test_parse_pointers_and_grade():
    ps = cl.parse_pointers(ROW["pointer"])
    assert ps == [("jar", "Nutrition.updateCalories @295 L118"), ("run", "exp03-20260910-045523 body.json rows.r1_baseline")]
    assert cl.strongest_grade([f for f, _ in ps]) == "M"
    assert cl.strongest_grade(["wiki", "jar"]) == "C" and cl.strongest_grade(["wiki"]) == "W"

def test_unknown_pointer_form_raises():
    try:
        cl.parse_pointers("book:p.12"); assert False
    except ValueError:
        pass

def test_parse_bound():
    assert cl.parse_bound("") == ("none", "")
    assert cl.parse_bound("n=2 boots; count census only") == ("n=2", "boots; count census only")
    assert cl.parse_bound("uncommitted: spike-20260909-143930") == ("uncommitted", "spike-20260909-143930")
    assert cl.parse_bound("snapshot 2026-09-10 17:47") == ("snapshot", "2026-09-10 17:47")
    try:
        cl.parse_bound("maybe n=1"); assert False
    except ValueError:
        pass

def test_canonical_suffix():
    assert cl.canonical_suffix(dict(ROW, grade="C", bound="", status="settled")) == ""
    assert cl.canonical_suffix(ROW) == "/M/n=1"
    assert cl.canonical_suffix(dict(ROW, grade="C", bound="inference", status="settled")) == "/C/inference"
    assert cl.canonical_suffix(dict(ROW, grade="C", bound="", status="open")) == "/C/open"
    assert cl.canonical_suffix(dict(ROW, grade="M", bound="uncommitted: x-1", status="unverified")) == "/M/uncommitted/unverified"

def test_tags():
    text = "Burn is 0.016 [#0001/M/n=1]. Two [#0002, #0003/W]. Not a tag [#12]. Provisional [T3.7].\nSecond line [#0004]."
    assert list(cl.iter_tags(text)) == [(1, "#0001", "/M/n=1"), (1, "#0002", ""), (1, "#0003", "/W"), (2, "#0004", "")]
    assert cl.PROVISIONAL_RX.findall(text) == ["[T3.7]"]

def test_blocks_and_ids():
    assert cl.block_of("#0001") == "G1a" and cl.block_of("#0450") == "G1b" and cl.block_of("#1121") == "G2c"
    assert cl.block_of("#2001") == "post" and cl.id_str(17) == "#0017" and cl.id_int("#0017") == 17

def test_validate_row():
    assert cl.validate_row(ROW) == []
    bad = dict(ROW, grade="C", kind="fact", owner="facts/body.md", status="superseded")
    errs = cl.validate_row(bad)
    assert any("grade" in e for e in errs) and any("kind" in e for e in errs)
    assert any("owner" in e for e in errs) and any("successor" in e for e in errs)
```

- [ ] **Step 2: Run to see them fail**

Run: `python -m pytest tools/tests/test_claimslib.py -q` → FAIL, `No module named 'claimslib'`.

- [ ] **Step 3: Write the library**

`tools/claimslib.py`:

```python
#!/usr/bin/env python3
"""The claims register: schema constants, TSV IO and the tag / pointer / bound grammars.

Spec: docs/superpowers/specs/2026-09-17-reference-restructure-design.md § The claims register."""
import re

COLUMNS = ("id", "claim", "grade", "pointer", "bound", "status", "successor", "kind", "source", "owner")
GRADES = ("C", "M", "W")
STATUSES = ("settled", "open", "superseded", "unverified")
KINDS = ("mechanism", "order", "table", "count", "verdict", "rule", "bound", "contradiction", "tool", "open")
BOUND_TOKENS = ("none", "one-side", "C-only", "one-fixture", "arith.", "inference", "uncommitted", "snapshot")
POINTER_FORMS = {"jar": "C", "run": "M", "wiki": "W", "lua": "C", "mod": "C", "repo": "C", "data": "C", "tool": "C"}
ANCHORED_FORMS = ("lua", "mod", "repo")           # these carry quoted anchor text
LAYERS = ("areas", "platform", "facts", "reference")
BLOCKS = (("G1a", 1, 200), ("G1b", 201, 450), ("G1c", 451, 600), ("G1d", 601, 800),
          ("G2a", 801, 1000), ("G2b", 1001, 1120), ("G2c", 1121, 1300),
          ("G3a", 1301, 1550), ("G3b", 1551, 1700), ("G4", 1701, 2000), ("post", 2001, 9999))
GRADE_RANK = {"M": 3, "C": 2, "W": 1}

ID_RX = re.compile(r"#\d{4}")
ID_FULL_RX = re.compile(r"^#\d{4}$")
_TAG_ITEM = r"#\d{4}(?:/[^\]\[,\s]+)*"
TAG_RX = re.compile(r"\[(" + _TAG_ITEM + r"(?:,\s*" + _TAG_ITEM + r")*)\]")
PROVISIONAL_RX = re.compile(r"\[T\d+\.\d+\]")
OWNER_RX = re.compile(r"^(areas|platform|facts|reference)/[A-Za-z0-9._/-]+\.md#[a-z0-9-]+$")
BOUND_N_RX = re.compile(r"^n=\d+$")
ANCHOR_RX = re.compile(r'"[^"]+"')


class RegisterError(Exception):
    pass


def id_int(s):
    return int(s[1:])


def id_str(n):
    return "#%04d" % n


def block_of(s):
    n = id_int(s)
    for name, lo, hi in BLOCKS:
        if lo <= n <= hi:
            return name
    return "none"


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
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(COLUMNS) + "\n")
        for r in rows:
            cells = [str(r.get(c, "")) for c in COLUMNS]
            for c in cells:
                if "\t" in c or "\n" in c:
                    raise RegisterError("%s: a cell contains a tab or newline: %r" % (r.get("id"), c[:60]))
            f.write("\t".join(cells) + "\n")


def parse_pointers(cell):
    """'jar:X @1 L2; run:id file key' -> [('jar', 'X @1 L2'), ('run', 'id file key')]."""
    out = []
    for part in [p.strip() for p in cell.split(";") if p.strip()]:
        form, sep, text = part.partition(":")
        form = form.strip()
        if not sep or form not in POINTER_FORMS:
            raise ValueError("unknown pointer form in %r" % part)
        out.append((form, text.strip()))
    return out


def strongest_grade(forms):
    grades = [POINTER_FORMS[f] for f in forms]
    return max(grades, key=lambda g: GRADE_RANK[g]) if grades else "C"


def parse_bound(cell):
    """('none', '') for empty; else (token, rest). Raises ValueError on an unknown first token."""
    cell = cell.strip()
    if not cell:
        return ("none", "")
    head, _, rest = cell.partition(" ")
    token = head.rstrip(":")
    if token in BOUND_TOKENS or BOUND_N_RX.match(token):
        return (token, rest.strip())
    raise ValueError("bound must start with a controlled token, got %r" % head)


def canonical_suffix(row):
    token, _ = parse_bound(row.get("bound", ""))
    grade, status = row["grade"], row["status"]
    if grade == "C" and token == "none" and status == "settled":
        return ""
    parts = [grade]
    if token != "none":
        parts.append(token)
    if status != "settled":
        parts.append(status)
    return "/" + "/".join(parts)


def split_tag(inner):
    """'#0417/M, #0512' -> [('#0417', '/M'), ('#0512', '')]."""
    out = []
    for item in [i.strip() for i in inner.split(",")]:
        cid, sep, rest = item.partition("/")
        out.append((cid, ("/" + rest) if sep else ""))
    return out


def iter_tags(text):
    for n, line in enumerate(text.splitlines(), 1):
        for m in TAG_RX.finditer(line):
            for cid, suffix in split_tag(m.group(1)):
                yield (n, cid, suffix)


def validate_row(row):
    """Schema errors for one row (empty list = valid). Cross-row checks live in claims_check."""
    errs = []
    if not ID_FULL_RX.match(row.get("id", "")):
        errs.append("id %r is not #dddd" % row.get("id"))
    if not row.get("claim", "").strip():
        errs.append("claim is empty")
    if row.get("grade") not in GRADES:
        errs.append("grade %r not in %s" % (row.get("grade"), GRADES))
    try:
        ptrs = parse_pointers(row.get("pointer", ""))
        if not ptrs:
            errs.append("pointer is empty")
        elif row.get("grade") in GRADES and strongest_grade([f for f, _ in ptrs]) != row["grade"]:
            errs.append("grade %s is not the strongest pointer grade" % row["grade"])
        for form, text in ptrs:
            if form in ANCHORED_FORMS and not ANCHOR_RX.search(text):
                errs.append("%s: pointer needs quoted anchor text: %r" % (form, text[:50]))
    except ValueError as e:
        errs.append(str(e))
    try:
        parse_bound(row.get("bound", ""))
    except ValueError as e:
        errs.append(str(e))
    if row.get("status") not in STATUSES:
        errs.append("status %r not in %s" % (row.get("status"), STATUSES))
    succ = row.get("successor", "").strip()
    if row.get("status") == "superseded" and not succ:
        errs.append("successor required when superseded")
    if row.get("status") != "superseded" and succ:
        errs.append("successor set on a non-superseded row")
    if succ and not all(ID_FULL_RX.match(s.strip()) for s in succ.split(",")):
        errs.append("successor %r is not #dddd[, #dddd]" % succ)
    if row.get("kind") not in KINDS:
        errs.append("kind %r not in %s" % (row.get("kind"), KINDS))
    if not row.get("source", "").strip():
        errs.append("source is empty")
    if row.get("status") != "superseded" and not OWNER_RX.match(row.get("owner", "")):
        errs.append("owner %r is not <layer>/<page>.md#<anchor>" % row.get("owner"))
    return errs
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `python -m pytest tools/tests/test_claimslib.py -q` → `9 passed`.

- [ ] **Step 5: Document and commit**

Append to `tools/README.md` `## Reference tooling`:

```markdown
- `claimslib.py` — no CLI. The claims register schema (`COLUMNS`, `KINDS`, `STATUSES`,
  `BOUND_TOKENS`, `POINTER_FORMS`, the id `BLOCKS`), TSV read/write, and the tag, pointer
  and bound grammars shared by `claims_harvest.py` and `claims_check.py`. The spec is
  `docs/superpowers/specs/2026-09-17-reference-restructure-design.md` § The claims register.
```

```bash
cd /c/Users/Angus/repos/project_zomboid && git commit -m "tools: claimslib (register schema and grammars)" -- tools/claimslib.py tools/tests/test_claimslib.py tools/README.md
```

---

### Task 4: `claims_harvest.py` — candidates, do-not-cite, merge

**Files:**
- Create: `tools/claims_harvest.py`
- Create: `tools/tests/test_claims_harvest.py`
- Modify: `tools/README.md` (`## Reference tooling`)

**Interfaces:**
- Consumes: `claimslib` (Task 3).
- Produces: `python tools/claims_harvest.py candidates <md files…> --out <tsv>` (one candidate per evidence-table row and per graded paragraph; columns `source line section kind_hint cells ev grades run_ids`); `python tools/claims_harvest.py do-not-cite <artifacts README> --out <csv>` (columns `run,key,value,why,read_instead`; a prose restriction without a key has `key = *`); `python tools/claims_harvest.py merge --parts <dir> --register <tsv> --coverage <md>` (concatenates `claims-*.tsv` sorted by id, fails on a duplicate id, writes the register; concatenates `coverage-*.md` in group order under a header and a totals table). Module functions `candidates(paths) -> list[dict]`, `do_not_cite(readme_path) -> list[dict]`, `merge(parts_dir) -> (rows, coverage_text)`.

- [ ] **Step 1: Write the failing tests**

`tools/tests/test_claims_harvest.py`:

```python
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import claims_harvest as ch
import claimslib as cl

CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "claims_harvest.py")

DOC = """# Body stats

Verified against: 42.20.4

## Passive burn

Idle burn is 0.016 per game-second — **M**, run `exp03-20260910-045523`, key `rows.r1_baseline`.

| Branch | Rate | Ev |
|---|---|---|
| idle | 0.016 | C `updateCalories @295 L118` |
| asleep | 0.003 | C+M `exp03-20260910-045523` |

```lua
-- Ev C inside a fence is not a candidate
```

## Milestones

All rows below are C (arith.).

| Milestone | Hours | Ev |
|---|---|---|
| level 1 | 4.70 | C (arith.) |
"""

README = """# Artifacts

#### `exp03-20260910-045523` — body.json

Reading guide prose.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| `summary.r12.allBandsMatch` | `false` | The two false bands are drift; read `rows.r12_weight_bands` per band instead. |
| `a.b` and `a.c` | `1` | Both are the driver's cap. |

- everything measured here, as a population — n = 1

#### `x121-20260911-030023` — platform-overrides.json

**Do not cite from `x121b-20260911-030099` (boot b):**

| Key | Value in the file | Why not |
|---|---|---|
| `phases.M3` | `earlier wins` | A reading, not a rule. |
"""

def _write(d, rel, text):
    p = os.path.join(d, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8", newline="\n").write(text); return p

def test_candidates_tables_paragraphs_and_fences():
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "docs/vanilla/body-stats.md", DOC)
        rows = ch.candidates([p])
        kinds = [(r["kind_hint"], r["section"]) for r in rows]
        assert kinds == [("paragraph", "Passive burn"), ("table", "Passive burn"), ("table", "Passive burn"),
                         ("paragraph", "Milestones"), ("table", "Milestones")]
        asleep = rows[2]
        assert asleep["ev"] == "C+M `exp03-20260910-045523`" and asleep["grades"] == "C,M"
        assert asleep["run_ids"] == "exp03-20260910-045523" and asleep["cells"].startswith("asleep | 0.003")
        assert rows[0]["run_ids"] == "exp03-20260910-045523"

def test_candidates_cli_writes_tsv():
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "doc.md", DOC); out = os.path.join(d, "c.tsv")
        r = subprocess.run([sys.executable, CLI, "candidates", p, "--out", out], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        lines = open(out, encoding="utf-8").read().splitlines()
        assert lines[0] == "source\tline\tsection\tkind_hint\tcells\tev\tgrades\trun_ids" and len(lines) == 6

def test_do_not_cite_blocks():
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "README.md", README)
        rows = ch.do_not_cite(p)
        assert [(r["run"], r["key"]) for r in rows] == [
            ("exp03-20260910-045523", "summary.r12.allBandsMatch"), ("exp03-20260910-045523", "a.b"),
            ("exp03-20260910-045523", "a.c"), ("exp03-20260910-045523", "*"),
            ("x121b-20260911-030099", "phases.M3")]
        assert rows[0]["read_instead"].startswith("read `rows.r12_weight_bands`")
        assert rows[3]["why"].startswith("everything measured here")

def test_merge_sorts_and_rejects_duplicates():
    with tempfile.TemporaryDirectory() as d:
        parts = os.path.join(d, "parts"); os.makedirs(parts)
        row = lambda i, k: {"id": cl.id_str(i), "claim": "c%d" % i, "grade": "C", "pointer": "jar:X.y @1 L2", "bound": "",
                            "status": "settled", "successor": "", "kind": k, "source": "s", "owner": "facts/x.md#a"}
        cl.write_register(os.path.join(parts, "claims-G1b.tsv"), [row(201, "table")])
        cl.write_register(os.path.join(parts, "claims-G1a.tsv"), [row(1, "mechanism"), row(2, "rule")])
        _write(parts, "coverage-G1a.md", "### a.md\n- § S — candidates 2 → rows #0001–#0002\n")
        _write(parts, "coverage-G1b.md", "### b.md\n- § T — candidates 1 → rows #0201\n")
        rows, cov = ch.merge(parts)
        assert [r["id"] for r in rows] == ["#0001", "#0002", "#0201"]
        assert "### a.md" in cov and cov.index("### a.md") < cov.index("### b.md") and "| mechanism | 1 |" in cov
        cl.write_register(os.path.join(parts, "claims-G1c.tsv"), [row(2, "mechanism")])
        try:
            ch.merge(parts); assert False, "duplicate id must raise"
        except cl.RegisterError:
            pass
```

- [ ] **Step 2: Run to see them fail**

Run: `python -m pytest tools/tests/test_claims_harvest.py -q` → FAIL, `No module named 'claims_harvest'`.

- [ ] **Step 3: Write the tool**

`tools/claims_harvest.py`:

```python
#!/usr/bin/env python3
"""Harvest helpers for the claims register.

candidates  : every evidence-table row and graded paragraph of the given docs -> a TSV checklist
do-not-cite : the artifacts README's "Do not cite" blocks -> docs/reference/do-not-cite.csv
merge       : docs/reference/parts/claims-*.tsv + coverage-*.md -> claims.tsv + claims-coverage.md
"""
import argparse, collections, csv, glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claimslib as cl

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_ID_RX = re.compile(r"\b[a-z0-9]+-2026\d{4}-\d{6}\b")
GRADE_LETTER_RX = re.compile(r"\b([CMW])\b")
GRADE_MARK_RX = re.compile(
    r"\bC \(arith\.?\)|\bC ?\+ ?M\b|\bM ?\+ ?C\b|\bW (?:vs\.?|\+) C\b|\bC \+ W\b|\*\*[CMW]\*\*"
    r"|\bEv[: ]+[CMW]\b|\b[CMW] \((?:run|runs|spike|jar|inference|arith)|\bgraded? [CMW]\b")
HEADING_RX = re.compile(r"^(#{1,4})\s+(.*?)\s*$")
CANDIDATE_COLUMNS = ("source", "line", "section", "kind_hint", "cells", "ev", "grades", "run_ids")
DNC_COLUMNS = ("run", "key", "value", "why", "read_instead")
DNC_MARK_RX = re.compile(r"^\*\*Do not cite from (?:this file|`([^`]+)`[^:]*):\*\*")
READ_INSTEAD_RX = re.compile(r"((?:read|use|take|cite)\b[^.;]*)", re.I)
GROUP_ORDER = ("G1a", "G1b", "G1c", "G1d", "G2a", "G2b", "G2c", "G3a", "G3b", "G4")


def _rel(path):
    return os.path.relpath(path, REPO_ROOT).replace("\\", "/") if os.path.isabs(path) else path.replace("\\", "/")


def _clean(s):
    return re.sub(r"\s+", " ", s.replace("\t", " ")).strip()


def _tables(lines):
    """(start_index, header_cells, [(index, cells)]) per markdown table, doc_lint's shape."""
    i = 0
    while i < len(lines):
        if lines[i].startswith("|") and i + 1 < len(lines) and re.match(r"^\|\s*:?-", lines[i + 1]):
            header = [c.strip() for c in lines[i].strip("|").split("|")]
            rows, j = [], i + 2
            while j < len(lines) and lines[j].startswith("|"):
                rows.append((j, [c.strip() for c in lines[j].strip("|").split("|")]))
                j += 1
            yield i, header, rows
            i = j
        else:
            i += 1


def candidates(paths):
    out = []
    for path in paths:
        text = open(path, encoding="utf-8", errors="replace", newline="").read()
        lines = [l.rstrip("\r") for l in text.split("\n")]
        section_at = {}
        section, fence, in_table = "", False, set()
        for idx, line in enumerate(lines):
            if line.startswith("```"):
                fence = not fence
            m = HEADING_RX.match(line)
            if m and not fence:
                section = m.group(2)
            section_at[idx] = (section, fence)
        for start, header, rows in _tables(lines):
            if section_at[start][1]:
                continue
            ev_cols = [k for k, c in enumerate(header) if c == "Ev" or c.startswith("Ev ")]
            if not ev_cols:
                continue
            for idx, cells in rows:
                in_table.add(idx)
                ev = cells[ev_cols[0]] if ev_cols[0] < len(cells) else ""
                out.append(_row(path, idx, section_at[idx][0], "table", " | ".join(cells), ev))
        for idx, line in enumerate(lines):
            if idx in in_table or section_at[idx][1] or line.startswith("|") or line.startswith("```"):
                continue
            m = GRADE_MARK_RX.search(line)
            if m:
                out.append(_row(path, idx, section_at[idx][0], "paragraph", line[:400], m.group(0)))
    out.sort(key=lambda r: (r["source"], int(r["line"])))
    return out


def _row(path, idx, section, kind_hint, cells, ev):
    grades = sorted(set(GRADE_LETTER_RX.findall(ev)) or set(GRADE_LETTER_RX.findall(cells)))
    run_ids = sorted(set(RUN_ID_RX.findall(ev)) | set(RUN_ID_RX.findall(cells)))
    return {"source": _rel(path), "line": str(idx + 1), "section": _clean(section), "kind_hint": kind_hint,
            "cells": _clean(cells), "ev": _clean(ev), "grades": ",".join(grades), "run_ids": ",".join(run_ids)}


def write_tsv(path, rows, columns):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(columns) + "\n")
        for r in rows:
            f.write("\t".join(_clean(str(r.get(c, ""))) for c in columns) + "\n")


def do_not_cite(readme_path):
    lines = [l.rstrip("\r") for l in open(readme_path, encoding="utf-8", errors="replace", newline="").read().split("\n")]
    out, current_run, i = [], "", 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#") or line.startswith("**"):
            m = RUN_ID_RX.search(line)
            if m and not DNC_MARK_RX.match(line):
                current_run = m.group(0)
        mark = DNC_MARK_RX.match(line)
        if not mark:
            i += 1
            continue
        run = mark.group(1) or current_run
        j = i + 1
        while j < len(lines) and (not lines[j].strip() or lines[j].startswith("|") or lines[j].startswith("- ")):
            if lines[j].startswith("|") and j + 1 < len(lines) and re.match(r"^\|\s*:?-", lines[j + 1]):
                j += 2
                while j < len(lines) and lines[j].startswith("|"):
                    cells = [c.strip() for c in lines[j].strip("|").split("|")]
                    keys = re.findall(r"`([^`]+)`", cells[0]) or [cells[0]]
                    value = cells[1] if len(cells) > 1 else ""
                    why = cells[2] if len(cells) > 2 else ""
                    for key in keys:
                        out.append(_dnc(run, key, value, why))
                    j += 1
                continue
            if lines[j].startswith("- "):
                out.append(_dnc(run, "*", "", lines[j][2:]))
            j += 1
        i = j
    return out


def _dnc(run, key, value, why):
    m = READ_INSTEAD_RX.search(why)
    return {"run": run, "key": _clean(key), "value": _clean(value), "why": _clean(why),
            "read_instead": _clean(m.group(1)) if m else ""}


def write_csv(path, rows, columns):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})


def merge(parts_dir):
    rows, seen = [], {}
    for part in sorted(glob.glob(os.path.join(parts_dir, "claims-*.tsv"))):
        for r in cl.read_register(part):
            if r["id"] in seen:
                raise cl.RegisterError("duplicate id %s in %s and %s" % (r["id"], seen[r["id"]], os.path.basename(part)))
            seen[r["id"]] = os.path.basename(part)
            rows.append(r)
    rows.sort(key=lambda r: cl.id_int(r["id"]))
    by = {"kind": collections.Counter(r["kind"] for r in rows), "grade": collections.Counter(r["grade"] for r in rows),
          "status": collections.Counter(r["status"] for r in rows), "block": collections.Counter(cl.block_of(r["id"]) for r in rows)}
    cov = ["# Claims coverage", "", "Per old source section: the candidates harvested into register rows, superseded, dropped "
           "(with the reason) or left unverified. Generated by `claims_harvest.py merge` from the harvest parts; "
           "%d rows." % len(rows), "", "## Totals", ""]
    for name in ("kind", "grade", "status", "block"):
        cov += ["| %s | rows |" % name, "|---|---|"] + ["| %s | %d |" % (k, v) for k, v in sorted(by[name].items())] + [""]
    parts = glob.glob(os.path.join(parts_dir, "coverage-*.md"))
    order = {g: n for n, g in enumerate(GROUP_ORDER)}
    for part in sorted(parts, key=lambda p: order.get(os.path.basename(p)[9:-3], 99)):
        cov += ["## " + os.path.basename(part)[9:-3], "", open(part, encoding="utf-8").read().strip(), ""]
    return rows, "\n".join(cov) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("candidates"); c.add_argument("paths", nargs="+"); c.add_argument("--out", required=True)
    d = sub.add_parser("do-not-cite"); d.add_argument("readme"); d.add_argument("--out", required=True)
    m = sub.add_parser("merge"); m.add_argument("--parts", default="docs/reference/parts")
    m.add_argument("--register", default="docs/reference/claims.tsv"); m.add_argument("--coverage", default="docs/reference/claims-coverage.md")
    a = ap.parse_args(argv)
    if a.cmd == "candidates":
        rows = candidates(a.paths); write_tsv(a.out, rows, CANDIDATE_COLUMNS)
        print("%d candidates -> %s" % (len(rows), a.out))
    elif a.cmd == "do-not-cite":
        rows = do_not_cite(a.readme); write_csv(a.out, rows, DNC_COLUMNS)
        print("%d do-not-cite rows -> %s" % (len(rows), a.out))
    else:
        rows, cov = merge(a.parts)
        cl.write_register(a.register, rows)
        open(a.coverage, "w", encoding="utf-8", newline="\n").write(cov)
        print("%d rows -> %s; coverage -> %s" % (len(rows), a.register, a.coverage))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `python -m pytest tools/tests/test_claims_harvest.py -q` → `4 passed`. If `test_candidates_tables_paragraphs_and_fences` disagrees on the paragraph count, print `rows` and fix the regex, not the test: the intent is one paragraph candidate per line carrying a grade mark outside tables and fences.

- [ ] **Step 5: Smoke it on the real tree**

Run: `cd /c/Users/Angus/repos/project_zomboid && python tools/claims_harvest.py candidates docs/vanilla/*.md --out .superpowers/sdd/restructure-1-register/smoke-vanilla.tsv && python tools/claims_harvest.py do-not-cite testing/artifacts/README.md --out .superpowers/sdd/restructure-1-register/smoke-dnc.csv`
Expected: about 800 candidates for the six vanilla docs (667 table rows plus paragraphs) and 40–80 do-not-cite rows. Read the first twenty lines of each output; a table row whose `ev` is empty or a run id split across cells is a parser defect to fix now.

- [ ] **Step 6: Document and commit**

Append to `tools/README.md` `## Reference tooling`:

```markdown
- `claims_harvest.py` — `python tools/claims_harvest.py candidates <md…> --out <tsv>` |
  `do-not-cite <artifacts README> --out <csv>` | `merge [--parts DIR] [--register TSV] [--coverage MD]`.
  `candidates` lists every body row of a table with an `Ev` column and every paragraph
  line carrying a grade mark (outside code fences), with the section heading, the evidence
  cell, the grade letters and run ids it names — the harvest checklist, not the register.
  `do-not-cite` turns the README's **Do not cite** blocks into `run,key,value,why,read_instead`
  rows (a prose restriction with no key has `key = *`). `merge` concatenates
  `parts/claims-*.tsv` sorted by id (a duplicate id fails), writes the register, and stitches
  `parts/coverage-*.md` under a totals table.
```

```bash
cd /c/Users/Angus/repos/project_zomboid && git commit -m "tools: claims_harvest (candidates, do-not-cite, merge)" -- tools/claims_harvest.py tools/tests/test_claims_harvest.py tools/README.md
```

---

### Task 5: `bus_inventory.py` — the harness command generator

**Files:**
- Create: `tools/bus_inventory.py`
- Create: `tools/tests/test_bus_inventory.py`
- Modify: `tools/README.md` (`## Reference tooling`)

**Interfaces:**
- Produces: `python tools/bus_inventory.py [--lua-dir DIR] [--out FILE] [--check]`; module functions `scan(lua_dir) -> list[dict(name, side, file, line, args, reply, purpose, missing)]`, `render(sites, label) -> str`. Exit 1 when any site lacks one of the three keys (the sites are listed on stderr) or, with `--check`, when the file differs from a fresh render. The comment block grammar the Lua must follow (Task 6 writes it): the contiguous run of `--` comment lines directly above `TK.register("<name>",` contains, in any order, `-- @args <argument line or (none)>`, `-- @reply <the reply keys in braces, or string, or unrecorded>`, `-- @purpose <one line>`; other comment lines may sit in the same run; the nearest occurrence of a key wins.
- Consumed by: Task 6 (writes the blocks and generates the file), Task 9 (rule 5 imports `render`/`scan`).

- [ ] **Step 1: Write the failing tests**

`tools/tests/test_bus_inventory.py`:

```python
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import bus_inventory as bi

CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bus_inventory.py")

SHARED = """function TK.register(name, fn) TK.commands[name] = fn end

-- an older comment line
-- @args (none)
-- @reply {ok, side}
-- @purpose Liveness check; answers on both sides.
TK.register("ping", function() return { ok = true } end)
"""
SERVER = """-- @purpose Read the player's Nutrition object.
-- @args <user>
-- @reply {calories, carbs, lipids, proteins, weight}
TK.register("nutrition.get", function(argv) return TK.nutritionSnapshot(findPlayer(argv[1])) end)

-- @args <user> <field> <value>
-- @purpose Server-side stats write.
TK.register("stats.set", function(argv) return 1 end)
"""
CLIENT = """-- @args (none)
-- @reply {calories, carbs, lipids, proteins, weight}
-- @purpose Read the local player's Nutrition copy.
TK.register("nutrition.get", function() return TK.nutritionSnapshot(getPlayer()) end)
"""

def _tree(d, server=SERVER):
    for side, text in (("shared", SHARED), ("server", server), ("client", CLIENT)):
        os.makedirs(os.path.join(d, side), exist_ok=True)
        open(os.path.join(d, side, "PZTestKit_%s.lua" % side.title()), "w", encoding="utf-8").write(text)
    return d

def test_scan_reads_blocks_and_reports_missing_keys():
    with tempfile.TemporaryDirectory() as d:
        sites = bi.scan(_tree(d))
        by = {(s["name"], s["side"]): s for s in sites}
        assert len(sites) == 4 and by[("ping", "shared")]["purpose"] == "Liveness check; answers on both sides."
        assert by[("nutrition.get", "server")]["args"] == "<user>" and by[("nutrition.get", "client")]["args"] == "(none)"
        assert by[("stats.set", "server")]["missing"] == ["reply"]
        assert by[("ping", "shared")]["file"] == "shared/PZTestKit_Shared.lua" and by[("ping", "shared")]["line"] == 7

def test_render_is_sorted_and_escapes_pipes():
    with tempfile.TemporaryDirectory() as d:
        sites = [s for s in bi.scan(_tree(d)) if not s["missing"]]
        sites[0]["purpose"] = "a | b"
        text = bi.render(sites, "lua")
        lines = [l for l in text.splitlines() if l.startswith("| `")]
        assert [l.split("|")[1].strip() for l in lines] == ["`nutrition.get`", "`nutrition.get`", "`ping`"]
        assert "server" in lines[0] and "client" in lines[1] and "a \\| b" in text
        assert "3 sites, 2 names" in text

def test_cli_fails_on_missing_key_and_checks_drift():
    with tempfile.TemporaryDirectory() as d:
        _tree(d); out = os.path.join(d, "harness-commands.md")
        r = subprocess.run([sys.executable, CLI, "--lua-dir", d, "--out", out], capture_output=True, text=True)
        assert r.returncode == 1 and "stats.set" in r.stderr and "reply" in r.stderr
        good = SERVER.replace("-- @purpose Server-side stats write.", "-- @reply string\n-- @purpose Server-side stats write.")
        _tree(d, server=good)
        assert subprocess.run([sys.executable, CLI, "--lua-dir", d, "--out", out], capture_output=True, text=True).returncode == 0
        assert subprocess.run([sys.executable, CLI, "--lua-dir", d, "--out", out, "--check"], capture_output=True, text=True).returncode == 0
        open(out, "a", encoding="utf-8").write("| `zzz` | server | `x:1` | a | b | c |\n")
        r = subprocess.run([sys.executable, CLI, "--lua-dir", d, "--out", out, "--check"], capture_output=True, text=True)
        assert r.returncode == 1 and "drift" in (r.stdout + r.stderr)
```

- [ ] **Step 2: Run to see them fail**

Run: `python -m pytest tools/tests/test_bus_inventory.py -q` → FAIL, `No module named 'bus_inventory'`.

- [ ] **Step 3: Write the generator**

`tools/bus_inventory.py`:

```python
#!/usr/bin/env python3
"""Generate docs/reference/harness-commands.md from every TK.register("<name>", ...) site.

Each site carries, in the contiguous `--` comment run directly above it:
    -- @args <argument line, or (none)>
    -- @reply <reply keys in braces, or string, or unrecorded>
    -- @purpose <one line>
A site missing any key fails the run (exit 1). `--check` fails (exit 1) when the file on disk
differs from a fresh render — the generated table can never trail the Lua."""
import argparse, glob, os, re, sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUA_DIR = os.path.join(REPO_ROOT, "testing", "PZTestKit", "PZTestKit", "42", "media", "lua")
OUT = os.path.join(REPO_ROOT, "docs", "reference", "harness-commands.md")
SIDES = ("shared", "server", "client")
KEYS = ("args", "reply", "purpose")
REGISTER_RX = re.compile(r'TK\.register\(\s*"([^"]+)"')
KEY_RX = re.compile(r"^\s*--\s*@(args|reply|purpose)\s+(.*\S)\s*$")


def scan(lua_dir):
    sites = []
    for side in SIDES:
        for path in sorted(glob.glob(os.path.join(lua_dir, side, "*.lua"))):
            lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
            for i, line in enumerate(lines):
                m = REGISTER_RX.search(line)
                if not m:
                    continue
                block, j = {}, i - 1
                while j >= 0 and lines[j].lstrip().startswith("--"):
                    km = KEY_RX.match(lines[j])
                    if km and km.group(1) not in block:
                        block[km.group(1)] = km.group(2)
                    j -= 1
                sites.append({"name": m.group(1), "side": side, "file": side + "/" + os.path.basename(path),
                              "line": i + 1, "args": block.get("args", ""), "reply": block.get("reply", ""),
                              "purpose": block.get("purpose", ""), "missing": [k for k in KEYS if k not in block]})
    return sites


def _cell(text):
    return text.replace("|", "\\|")


def render(sites, label):
    order = {s: n for n, s in enumerate(SIDES)}
    rows = sorted(sites, key=lambda s: (s["name"], order[s["side"]]))
    names = len({s["name"] for s in rows})
    out = ["# Harness commands", "",
           "GENERATED by `python tools/bus_inventory.py` from every `TK.register(...)` site under `%s` — do not edit "
           "this file; edit the `-- @args` / `-- @reply` / `-- @purpose` block above the site and regenerate. "
           "One row per (name, side): a name registered on two sides takes different arguments per side. "
           "The reply-reading rules (the three buckets, `{}` for an empty list, `resolved`, `limit` is a BREAK) are "
           "`docs/platform/harness.md`, not this table. %d sites, %d names." % (label, len(rows), names), "",
           "| name | side | file:line | args | reply keys | purpose |", "|---|---|---|---|---|---|"]
    for s in rows:
        out.append("| `%s` | %s | `%s:%d` | %s | %s | %s |" % (
            s["name"], s["side"], s["file"], s["line"], _cell(s["args"]), _cell(s["reply"]), _cell(s["purpose"])))
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lua-dir", default=LUA_DIR)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--check", action="store_true", help="compare the file on disk with a fresh render; exit 1 on drift")
    a = ap.parse_args(argv)
    sites = scan(a.lua_dir)
    if not sites:
        print("no TK.register sites under %s" % a.lua_dir, file=sys.stderr)
        return 1
    missing = [s for s in sites if s["missing"]]
    if missing:
        for s in missing:
            print("%s:%d %s (%s): missing %s" % (s["file"], s["line"], s["name"], s["side"], ", ".join(s["missing"])), file=sys.stderr)
        print("%d of %d sites lack a complete @args/@reply/@purpose block" % (len(missing), len(sites)), file=sys.stderr)
        return 1
    label = os.path.relpath(a.lua_dir, REPO_ROOT).replace("\\", "/") if os.path.isabs(a.lua_dir) else a.lua_dir
    text = render(sites, label)
    if a.check:
        on_disk = open(a.out, encoding="utf-8", newline="").read().replace("\r\n", "\n") if os.path.exists(a.out) else ""
        if on_disk != text:
            old, new = on_disk.splitlines(), text.splitlines()
            first = next((n for n, (x, y) in enumerate(zip(old, new), 1) if x != y), min(len(old), len(new)) + 1)
            print("drift: %s differs from a fresh render at line %d (%d lines on disk, %d rendered); run without --check to regenerate"
                  % (a.out, first, len(old), len(new)))
            return 1
        print("in sync: %s (%d sites)" % (a.out, len(sites)))
        return 0
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "w", encoding="utf-8", newline="\n").write(text)
    print("wrote %s (%d sites, %d names)" % (a.out, len(sites), len({s["name"] for s in sites})))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `python -m pytest tools/tests/test_bus_inventory.py -q` → `3 passed`.

- [ ] **Step 5: Run it against the real harness to list the sites without blocks**

Run: `cd /c/Users/Angus/repos/project_zomboid && python tools/bus_inventory.py --out .superpowers/sdd/restructure-1-register/harness-commands.smoke.md; echo exit=$?`
Expected: exit 1 and 64 lines on stderr naming every site (none carries a block yet) — that list is Task 6's checklist. Save it: rerun with `2> .superpowers/sdd/restructure-1-register/sites-without-blocks.txt`.

- [ ] **Step 6: Document and commit**

Append to `tools/README.md` `## Reference tooling`:

```markdown
- `bus_inventory.py` — `python tools/bus_inventory.py [--lua-dir DIR] [--out FILE] [--check]`
  Generates `docs/reference/harness-commands.md` (one row per `TK.register` site and side:
  name · side · `file:line` · args · reply keys · purpose) from the `-- @args` / `-- @reply` /
  `-- @purpose` comment block directly above each site; a site without all three fails the
  run and is listed on stderr. `--check` exits 1 when the file on disk is not a fresh render.
  A harness commit that adds or changes a command edits the block and regenerates in the
  same commit (`claims_check.py` rule 5 enforces it).
```

```bash
cd /c/Users/Angus/repos/project_zomboid && git commit -m "tools: bus_inventory (harness command generator)" -- tools/bus_inventory.py tools/tests/test_bus_inventory.py tools/README.md
```

---

### Task 6: The comment blocks above every `TK.register` site, and the generated table

**Files:**
- Modify (comments only): `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua`, `shared/PZTestKit_Test.lua`, `server/PZTestKit_Server.lua`, `server/PZTestKit_Server_Recipes.lua`, `client/PZTestKit_Client.lua`, `client/PZTestKit_Client_Body.lua`
- Create (generated): `docs/reference/harness-commands.md`

**Interfaces:**
- Consumes: `tools/bus_inventory.py` (Task 5) and its block grammar; `tools/luabalance.py` (Task 2); the site list `.superpowers/sdd/restructure-1-register/sites-without-blocks.txt` (Task 5, Step 5).
- Produces: 64 sites each carrying `-- @args`, `-- @reply`, `-- @purpose` directly above `TK.register(`; `docs/reference/harness-commands.md` in sync.

This is the one harness edit of the restructure. It changes no behaviour: only comment lines are added. It lands in its own commit before the acceptance run (Task 20), which is its smoke test.

- [ ] **Step 1: Record the line endings and the baseline balance**

```bash
cd /c/Users/Angus/repos/project_zomboid && L=testing/PZTestKit/PZTestKit/42/media/lua && git ls-files --eol $L/shared/*.lua $L/server/*.lua $L/client/*.lua && python tools/luabalance.py $L/shared/*.lua $L/server/*.lua $L/client/*.lua
```

Expected: every file `BALANCED`; note each file's `w/` ending (`lf` or `crlf`) and preserve it when editing (the Write tool preserves what the Edit tool sees; if a file is `crlf`, every inserted line must be CRLF too — check with `git diff --stat` that the whole file did not change).

- [ ] **Step 2: Read the seeds**

Read `docs/testing/README.md` from the line `- **Command bus**` (about line 101) to the end of the command inventory (before `### Harness layout`, about line 749): it documents 42 of the 56 names with their argument shapes and reply shapes. Read each Lua file in full. For the 14 names the README does not document (`eat`, `fluid.script`, `foodtimer.set`, `item.age`, `item.age.tick`, `item.freeze`, `item.use`, `lua.reload`, `moddata.transmit`, `nutrition.applytraits`, `perk.xp`, `player.sleep`, `recipe.evolved`, `trait.set`) the purpose comes from the function body alone.

- [ ] **Step 3: Write the 64 blocks**

For every site in `sites-without-blocks.txt`, insert directly above the `TK.register("<name>", function…` line (below any comment run already there, so the block is the last thing before the call):

```lua
-- @args <user> <calories|carbs|lipids|proteins|weight> <value>
-- @reply {calories, weight, carbs, lipids, proteins, …the keys TK.nutritionSnapshot returns…} | string
-- @purpose Server-side write of one Nutrition field; the reply is the post-write snapshot.
```

Rules for the three lines:
- `@args`: the argument line as the function reads `argv` (`argv[1]` first); the `usage:` string in the body is the seed when there is one; a server twin of a client command takes `<user>` first; a function that ignores `argv` gets `(none)`. Optional arguments in `[brackets]`, alternatives with `|`.
- `@reply`: the keys of the table the function returns, in braces, in the order the code builds them; `string` when it returns a string; `{…} | string` when it returns a table on success and a string on error (the common shape: `"no online player …"`, `"usage: …"`); when the table comes from a helper (`TK.nutritionSnapshot`, `TK.bodySnapshot`, `TK.itemState`, `TK.json` of a built table), list that helper's keys by reading it in `PZTestKit_Core.lua` — write `unrecorded` only when the keys genuinely depend on runtime data (a reflective dump), and say so in the purpose. Never guess a key.
- `@purpose`: one line, present tense, what the command does and on which side it answers; the README's sentence trimmed where it exists.

Never touch a line that is not a comment. Never reorder sites.

- [ ] **Step 4: Balance and generate**

```bash
cd /c/Users/Angus/repos/project_zomboid && L=testing/PZTestKit/PZTestKit/42/media/lua && python tools/luabalance.py $L/shared/*.lua $L/server/*.lua $L/client/*.lua && python tools/bus_inventory.py && python tools/bus_inventory.py --check && git diff --stat
```

Expected: every file `BALANCED`; `wrote docs/reference/harness-commands.md (64 sites, 56 names)`; `in sync`; the diff stat shows only insertions on the six Lua files (no deletions — a deletion means a line ending or a non-comment line changed; fix before going on).

- [ ] **Step 5: Read the generated table once**

Open `docs/reference/harness-commands.md`: 64 rows, sorted by name then side; the eight doubled names (`nutrition.get`, `nutrition.set`, `stats.get`, `stats.set`, `perk.set`, `item.script`, `sandbox.set`, `moddata.set`) show two rows with different `args`. A row whose purpose repeats its name adds nothing — rewrite the block.

- [ ] **Step 6: Tests, then commit**

Run: `python -m pytest tools/tests testing/tests -q 2>&1 | tail -1` → green (283 + the new tests from Tasks 2–5).

```bash
cd /c/Users/Angus/repos/project_zomboid && L=testing/PZTestKit/PZTestKit/42/media/lua && git commit -m "Harness: @args/@reply/@purpose block above every TK.register site; harness-commands.md generated" -- $L/shared/PZTestKit_Core.lua $L/shared/PZTestKit_Test.lua $L/server/PZTestKit_Server.lua $L/server/PZTestKit_Server_Recipes.lua $L/client/PZTestKit_Client.lua $L/client/PZTestKit_Client_Body.lua docs/reference/harness-commands.md
```

The README inventory line rule (`CLAUDE.md` § 7) does not apply: no command was added or changed. Say so in the report.

---

### Task 7: The moved reference files, the run alias table and the driver template

**Files:**
- Create: `docs/reference/experiments.md` (from `.superpowers/sdd/13-wall-map/gaps.md`), `docs/reference/jar-method-notes.md` (from `.superpowers/sdd/13-wall-map/jar-locks.md`), `docs/reference/run-aliases.csv`, `testing/experiments/_template.py`, `testing/tests/test_template.py`

**Interfaces:**
- Produces: `run-aliases.csv` with header `alias,run,file,key` (read by Task 9's rule 3); the two reference files harvest tasks G2c and G4 cite as `source`; a driver template that runs without a game under `PZT_TEMPLATE_DRY_RUN=1`.

- [ ] **Step 1: Move the experiment specs**

Confirm the boundaries by content (line numbers drift): in `gaps.md`, the section `## The standing spec contract — every `Shape:` cell below inherits all six clauses` (about line 26) through the `---` before `## Step 5 — no commit` (about line 303). Then:

```bash
cd /c/Users/Angus/repos/project_zomboid && S=$(grep -n '^## The standing spec contract' .superpowers/sdd/13-wall-map/gaps.md | cut -d: -f1) && E=$(grep -n '^## Step 5' .superpowers/sdd/13-wall-map/gaps.md | cut -d: -f1) && mkdir -p docs/reference && { printf '%s\n' '# Named experiments — the full specs' '' 'Moved verbatim on 2026-09-17 from the slice-13 working read (`gaps.md`, gitignored until the restructure) so every register `source` resolves from a clone. Outside the page contract. The condensed table is `docs/reference/wall-map.md` § Named experiments; `docs/areas/open-questions.md` indexes both. The standing contract below becomes the rules of `docs/platform/harness.md`.' ''; sed -n "${S},$((E-1))p" .superpowers/sdd/13-wall-map/gaps.md; } > docs/reference/experiments.md && wc -l docs/reference/experiments.md && grep -c '^### \|^| X' docs/reference/experiments.md
```

Expected: about 285 lines; 26 `| X` rows are present (count them: `grep -cE '^\| \*\*?X[0-9]+' docs/reference/experiments.md` should print 26 or more).

- [ ] **Step 2: Move the jar method notes**

By content: the paragraph starting `**Tool note (bounds on every "absence" below).**` (about lines 12–20), the bash block that begins `./pz.sh grep checksum | grep -i script` (about lines 905–920, fenced), and the section `## Summary — where the jar disagrees with plan 13` to the end of the file (about lines 1103–1124). Assemble with the Write tool:

```markdown
# Reading the jar — method notes

Moved verbatim on 2026-09-17 from the slice-13 working read (`jar-locks.md`, gitignored until the restructure). Outside the page contract. The disassembler is **not in this repository**: `C:\Users\Angus\pz-b42\pz.sh` (`grep|methods|refs|dump`; `pz-b42/tools/pzdis.py`, `cp.py`, `dis.py`) against `D:\SteamLibrary\steamapps\common\ProjectZomboid\projectzomboid.jar` (42.20.4, `b0bbce05d5`), read-only. `docs/platform/jar-research.md` is written from the `tool` rows harvested here.

## Tool note

<the Tool note paragraph, verbatim>

## A worked query — the script checksum gate

<the fenced bash block, verbatim>

## Summary — where the jar disagreed with plan 13

<the section, verbatim, including the closing "Method-note the later tasks should carry" paragraph>
```

- [ ] **Step 3: The run alias table**

```bash
cd /c/Users/Angus/repos/project_zomboid && grep -n 'no folder of its own\|two boots in one' testing/artifacts/README.md
```

Expected: only `x123b-20260911-034500` (boot (b) of `x123`, stored under `boots.common_id` in `platform-folder.json`). Write `docs/reference/run-aliases.csv`:

```
alias,run,file,key
x123b-20260911-034500,x123-20260911-034426,platform-folder.json,boots.common_id
```

If the grep shows another aliased boot, add its row.

- [ ] **Step 4: Write the failing template test**

`testing/tests/test_template.py`:

```python
import json, os, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE = os.path.join(REPO, "testing", "experiments", "_template.py")

def test_template_dry_run_prints_provenance_and_boots_nothing():
    env = dict(os.environ, PZT_TEMPLATE_DRY_RUN="1")
    r = subprocess.run([sys.executable, TEMPLATE], capture_output=True, text=True, env=env, cwd=REPO, timeout=120)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    for key in ("run_id", "session", "profile", "commit", "harness_lua_commit", "harness_lua_dirty",
                "doctor_clean", "acceptance_run", "phases", "dry_run"):
        assert key in out, key
    assert out["dry_run"] is True and out["phases"] == {} and out["doctor_clean"] is None
```

Run: `python -m pytest testing/tests/test_template.py -q` → FAIL (`_template.py` does not exist).

- [ ] **Step 5: Cut the template from `x121_overrides.py`**

Read `testing/experiments/x121_overrides.py` in full. Create `testing/experiments/_template.py` with, in this order (copy each named block verbatim from `x121`, then strip what the comments below say):

1. A module docstring that says what a driver is (the house shape: provenance keys, client-first paired reads, wall-bracketed steps with measured offsets, `field_count` asserts, predictions/observations/verdicts `as_predicted | falsified | trivial | unmeasured`, try/except/finally that always saves the artifact and copies it byte-for-byte into `testing/artifacts/<run-id>/`), how to start a new driver (copy this file to `xNNN_<topic>.py`, set `PROFILE`, `SESSION`, `ARTIFACT`, write phases), and the two rules a driver never breaks (never edited after its run; readings that come back trivial or unmeasured are written as such).
2. The imports block of `x121` (`json os re shutil sys time traceback`; the two `sys.path.insert`; `from _common import ask, doctor, git_dirty, git_say, hard_kill, num, save`; `from pzt import fixture as fx, profile`; `from pzt.paths import new_run_dir`; `from pzt.session import Timeline, make_client, make_server, teardown, verify`).
3. Constants: `PROFILE = "mod-under-test"`, `SESSION = "template -- describe the session in one line"`, `ARTIFACT = "template.json"`, `USER = "pzt"` (x121's user constant, same value), `ACCEPTANCE_RUN = "<the acceptance run id this driver was smoke-tested against>"`, `REPO`, `LUA_DIR` as in `x121`, `DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"`.
4. The helper functions `wall`, `note`, `probe`, `step`, `grade` copied verbatim from `x121` (locate them by name; they sit together after the constants), with any reference to an x121-specific constant removed.
5. Setup: `prof = profile.load(PROFILE)`, `rec = fx.load(prof.fixture)`, `run_id, run_dir = new_run_dir("template")`, `path = os.path.join(run_dir, ARTIFACT)`, `tl, clients, t0 = Timeline(), [], time.time()`; then `server = None if DRY_RUN else make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip, sandbox=prof.sandbox or None)`; `doctor_clean, doctor_text = (None, "") if DRY_RUN else doctor()`; `lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)`.
6. The `out` dict with exactly the provenance keys `x121` writes — `run_id`, `session`, `user`, `profile` (`prof.report()`), `mods`, `commit`, `harness_lua_commit`, `harness_lua_dirty`, `harness_lua_dirty_note`, `doctor_clean`, `doctor`, `acceptance_run` — plus `"dry_run": DRY_RUN`, `"phases": {}`, `"world_changes": {"restored": "", "left_in_place": []}`.
7. The body: `if DRY_RUN:` print `json.dumps(out)` and `sys.exit(0)`; else the `try:` with one example phase `P1` that sends `ping` on both sides through `step(...)` and grades it with `grade("P1", predicted="ok on both sides", observed=..., verdict="as_predicted", falsifier="a side that does not answer")`, then `except Exception as e:` and `finally:` copied verbatim from the tail of `x121` (the `save`, `teardown`, `hard_kill`, the second `save`, the byte copy into `testing/artifacts/<run_id>/<ARTIFACT>`), and the final `print(json.dumps(...))`.

Nothing in it measures anything; every `x121` phase, constant and regex that is not named above is left out.

- [ ] **Step 6: Run the test to see it pass**

Run: `python -m pytest testing/tests/test_template.py -q` → `1 passed`. The dry run must not start java: confirm with `tasklist | grep -i java` before and after (no new process).

- [ ] **Step 7: Commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git commit -m "Reference: experiments.md and jar-method-notes.md moved into the tree; run aliases; driver template" -- docs/reference/experiments.md docs/reference/jar-method-notes.md docs/reference/run-aliases.csv testing/experiments/_template.py testing/tests/test_template.py
```

---

### Task 8: The anchor plan (deliverable 0 of the harvest)

**Files:**
- Create: `docs/superpowers/plans/restructure-anchors.md`

**Interfaces:**
- Produces: for every page of the spec's target tree (8 `areas/`, 8 `platform/`, 7 `facts/` plus 6 `facts/other-mods/`, and `reference/wall-map.md`), the list of anchors a register row may name as its `owner`. Every harvest task (10–18) and every Phase 2/3 page writer reads it. The file is grep-able: every anchor line has the form `` - `#<slug>` — <one line: what claims live here> ``.

- [ ] **Step 1: Read the inputs**

In this order: the spec § The target tree, § Placement rule, § Sync placement, § The hard cases, § The page contract; the platform review's Appendix D (`.superpowers/spec-review/2026-09-17-restructure/review-platform.md`, the section `## Appendix D`) — the seed anchor lists for the eight platform pages and the routing rule for `overview.md`; the nutrition review's Appendix A and Appendix C (`review-nutrition.md`, `## Appendix A` and `## Appendix C`) — the facts pages' content map and the split of `food-item-model` into three pages; the six slice-14 briefs (`.superpowers/sdd/14-feasibility-notes/task-1-brief.md` … `task-6-brief.md`) — the areas pages' content; `docs/modding/wall-map.md` § The map (the 64 row ids) for `reference/wall-map.md`.

- [ ] **Step 2: Write the file**

```markdown
# Anchor plan — the owners a register row may name

Deliverable 0 of the harvest (spec § The target tree, "The anchor plan"). A row's `owner` is `<page>#<slug>` from this file. A harvester that needs an anchor this file lacks writes `<page>#<new-slug>` and lists it under `## Anchors proposed` in its coverage part; the merge task folds the proposals in here. From Phase 2 on, the page carries the anchors and this file is the writers' checklist.

Rules: an anchor names one mechanism, one table or one reading; no anchor appears on two pages; `platform/overview.md` owns routing anchors only (no number of its own); a `facts/` page owns measured properties of the food, body or nutrition systems; an `areas/` page owns readings and options, never a mechanism; `reference/wall-map.md` owns exactly the 64 row ids.

## platform/overview.md
- `#surfaces` — the four surfaces a mod touches (scripts, Lua, translations, packets)
- `#two-lua-states` — server VM and client VM; a mod's `server/` file runs in both
…

## platform/mod-anatomy.md
- `#mod-info-keys` — every `mod.info` key and what the loader does with it
…
```

One `## <page>` section per page, in the tree's order. Use the platform review's Appendix D lists verbatim for the eight platform pages (`harness.md` included), the nutrition review's Appendix A targets for the seven facts pages (with `#sandbox` on every facts page that has a sandbox option, `#walls` on every page for contradiction rows), one section per `other-mods/` page with `#what-it-does`, `#techniques`, `#pitfalls`, `#compat`, `#mp` (the last citing `facts/wire-packets.md` rows, never restating), a `catalog.md` section with `#sweep`, `#status`, `#api-surface`, `#corpus-facts`, the eight areas pages with anchors that name readings and options (`#store-options`, `#sync-route`, `#persistence`, `#effect-paths` for `new-nutrients.md`, and so on from the briefs), and `reference/wall-map.md` with the 64 row ids `#a1` … `#j5` as anchors (lower-case).

- [ ] **Step 3: Self-check, then commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && grep -oE '^- `#[a-z0-9-]+`' docs/superpowers/plans/restructure-anchors.md | sort | uniq -d | head; grep -c '^## ' docs/superpowers/plans/restructure-anchors.md
```

Expected: no duplicated anchor slug within the file (duplicates across pages are allowed only for the generic `#walls`, `#sandbox`, `#open`); 30 page sections. Then:

```bash
git commit -m "Anchor plan for the claims register" -- docs/superpowers/plans/restructure-anchors.md
```

The reviewer of this task checks: every mechanism named in the spec's tree blurbs has exactly one anchor; the hard cases are honoured (the per-key merge on `loader-and-scripts`, the checksum gate's three arms on `mod-anatomy`, the registries on `lua-platform`, the harness on `platform/harness`, the field lists on `wire-packets`); no `areas/` anchor names a mechanism; `overview.md` has no fact anchor.

---

### Task 9: `claims_check.py` — the checker

**Files:**
- Create: `tools/claims_check.py`
- Create: `tools/tests/test_claims_check.py`
- Modify: `tools/README.md` (`## Reference tooling`)

**Interfaces:**
- Consumes: `claimslib` (Task 3), `bus_inventory.scan/render` (Task 5), `docs/reference/run-aliases.csv` (Task 7), `docs/reference/do-not-cite.csv` (Task 10).
- Produces: `python tools/claims_check.py [--root DIR] [--register TSV] [--lua-dir DIR] [--register-only] [--partial] [--staged] [--allow-provisional] [--fix-tags] [--view LAYER] [--section-map]`. Prints `path:line: rule: detail` per finding, then `N findings, M warnings`; exit 1 iff findings. Rules: `schema` (rule 0: every column's grammar, duplicate ids, contiguity from each sub-block's first id, successor ids exist), `owner` (rule 1), `tag` (rule 2), `pointer` (rule 3), `untagged` (rule 4, warning only), `generator` (rule 5), `skill` (rule 6), `example` (rule 7). `--register-only` runs `schema` and `pointer` only (the Phase 1 mode; every harvest part is checked with `--register <part>`). `--partial` lets rule 1 skip rows whose owner page does not exist yet (Phase 2/3 mode). `--staged` exits 0 without checking when no staged path is under `docs/`, `.claude/skills/`, `testing/PZTestKit/`, `testing/artifacts/`, `testing/experiments/` or `tools/bus_inventory.py`.

- [ ] **Step 1: Write the failing tests**

`tools/tests/test_claims_check.py`:

```python
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
        by = {x.detail.split(":")[0].strip(): x for x in f}
        ids = sorted(x.line for x in f)
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
```

- [ ] **Step 2: Run to see them fail**

Run: `python -m pytest tools/tests/test_claims_check.py -q` → FAIL, `No module named 'claims_check'`.

- [ ] **Step 3: Write the checker**

`tools/claims_check.py`:

```python
#!/usr/bin/env python3
"""The claims checker (spec § The checker and the generator).

Rules: schema (0) · owner (1) · tag (2) · pointer (3) · untagged (4, warning only) · generator (5)
· skill (6) · example (7). --register-only runs 0 and 3; --partial lets 1 skip owner pages that do
not exist yet; --fix-tags rewrites every tag's suffix from the register; --view LAYER and
--section-map print register slices; --staged skips the run when nothing relevant is staged."""
import argparse, collections, csv, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claimslib as cl

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = "docs/reference/claims.tsv"
DNC = "docs/reference/do-not-cite.csv"
ALIASES = "docs/reference/run-aliases.csv"
HARNESS_MD = "docs/reference/harness-commands.md"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
LAYER_DIRS = ("docs/areas", "docs/platform", "docs/facts")
SKILLS_DIR = ".claude/skills"
TRIGGERS = ("docs/", ".claude/skills/", "testing/PZTestKit/", "testing/artifacts/", "testing/experiments/", "tools/bus_inventory.py")
Finding = collections.namedtuple("Finding", "path line rule detail")
WARN_RULES = ("untagged",)
H2_RX = re.compile(r"^## (.+?)\s*$")
CODE_SPAN_RX = re.compile(r"`[^`]*`")
FILE_LINES_RX = re.compile(r"`?([A-Za-z0-9_./-]+\.[A-Za-z0-9]+):\d+(?:[-–]\d+)?`?")


def is_warning(f):
    return f.rule in WARN_RULES


def exit_code(findings):
    return 1 if any(not is_warning(f) for f in findings) else 0


def _rel(path, root):
    return os.path.relpath(path, root).replace("\\", "/")


def _read(path):
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        return f.read()


def _md_files(root, dirs):
    for d in dirs:
        base = os.path.join(root, *d.split("/"))
        for dp, _, fns in os.walk(base):
            for fn in sorted(fns):
                if fn.endswith(".md"):
                    yield os.path.join(dp, fn)


def _sections(text):
    """[(heading or '', [(lineno, line), ...])] split on '## ' headings; fences and tables kept as lines."""
    out, cur, lines = [], ("", []), text.replace("\r\n", "\n").split("\n")
    for n, line in enumerate(lines, 1):
        m = H2_RX.match(line)
        if m:
            out.append(cur); cur = (m.group(1), [])
        else:
            cur[1].append((n, line))
    out.append(cur)
    return out


def _load_csv(path, key):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8", newline="") as f:
        return {r[key]: r for r in csv.DictReader(f)} if key else list(csv.DictReader(f))


def rule_schema(rows, register_rel):
    out, seen = [], {}
    for n, r in enumerate(rows, 2):
        for e in cl.validate_row(r):
            out.append(Finding(register_rel, n, "schema", "%s: %s" % (r.get("id"), e)))
        if r["id"] in seen:
            out.append(Finding(register_rel, n, "schema", "%s: duplicate id (first at line %d)" % (r["id"], seen[r["id"]])))
        seen.setdefault(r["id"], n)
    ids = {r["id"] for r in rows}
    for r in rows:
        for s in [s.strip() for s in r.get("successor", "").split(",") if s.strip()]:
            if s not in ids:
                out.append(Finding(register_rel, seen.get(r["id"], 1), "schema", "%s: successor %s is not in the register" % (r["id"], s)))
    by_block = collections.defaultdict(set)
    for r in rows:
        if cl.ID_FULL_RX.match(r["id"]):
            by_block[cl.block_of(r["id"])].add(cl.id_int(r["id"]))
    for name, lo, hi in cl.BLOCKS:
        used = by_block.get(name)
        if used:
            expected = set(range(lo, lo + len(used)))
            if used != expected:
                missing = sorted(expected - used)[:5]
                out.append(Finding(register_rel, 1, "schema", "block %s: ids are not contiguous from %s (gap at %s)"
                                   % (name, cl.id_str(lo), ", ".join(cl.id_str(m) for m in missing))))
    return out


def rule_pointer(rows, root, register_rel):
    out = []
    dnc = {(r["run"], r["key"]) for r in _load_csv(os.path.join(root, DNC), None) or []}
    aliases = _load_csv(os.path.join(root, ALIASES), "alias")
    for n, r in enumerate(rows, 2):
        try:
            ptrs = cl.parse_pointers(r["pointer"])
        except ValueError:
            continue
        for form, text in ptrs:
            if form == "run":
                parts = text.split()
                run = parts[0] if parts else ""
                real = aliases[run]["run"] if run in aliases else run
                rdir = os.path.join(root, "testing", "artifacts", real)
                if not os.path.isdir(rdir):
                    out.append(Finding(register_rel, n, "pointer", "%s: run %s has no folder under testing/artifacts/ (no alias either)" % (r["id"], run)))
                    continue
                if len(parts) >= 2 and parts[1].endswith(".json") and not os.path.exists(os.path.join(rdir, parts[1])):
                    out.append(Finding(register_rel, n, "pointer", "%s: %s has no file %s" % (r["id"], real, parts[1])))
                key = " ".join(parts[2:]) if len(parts) >= 3 else ""
                if (real, key) in dnc or (run, key) in dnc:
                    out.append(Finding(register_rel, n, "pointer", "%s: %s %s is on the do-not-cite list" % (r["id"], real, key)))
            elif form == "repo":
                path = text.split('"')[0].strip().rsplit(":", 1)[0]
                if not os.path.exists(os.path.join(root, *path.split("/"))):
                    out.append(Finding(register_rel, n, "pointer", "%s: repo path %s does not exist" % (r["id"], path)))
    return out


def rule_owner(rows, root, partial):
    out = []
    for r in rows:
        if r["status"] == "superseded" or not cl.OWNER_RX.match(r["owner"]):
            continue
        page = r["owner"].split("#")[0]
        path = os.path.join(root, "docs", *page.split("/"))
        if not os.path.exists(path):
            if not partial:
                out.append(Finding("docs/" + page, 1, "owner", "%s: owner page does not exist" % r["id"]))
            continue
        if r["id"] not in {cid for _, cid, _ in cl.iter_tags(_read(path))}:
            out.append(Finding("docs/" + page, 1, "owner", "%s: owner page carries no tag for it" % r["id"]))
    return out


def rule_tag(rows, root, allow_provisional):
    out, by_id = [], {r["id"]: r for r in rows}
    for path in list(_md_files(root, LAYER_DIRS)) + _skill_files(root):
        rel, text = _rel(path, root), _read(path)
        for n, cid, suffix in cl.iter_tags(text):
            if cid not in by_id:
                out.append(Finding(rel, n, "tag", "%s is not in the register" % cid))
            else:
                want = cl.canonical_suffix(by_id[cid])
                if suffix != want:
                    out.append(Finding(rel, n, "tag", "%s: suffix %r should be %r (run --fix-tags)" % (cid, suffix, want)))
        if not allow_provisional:
            for n, line in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
                for m in cl.PROVISIONAL_RX.findall(line):
                    out.append(Finding(rel, n, "tag", "provisional tag %s (apply the delta, or --allow-provisional)" % m))
    return out


def rule_untagged(root):
    out = []
    for path in _md_files(root, LAYER_DIRS):
        rel, fence = _rel(path, root), False
        for heading, lines in _sections(_read(path)):
            if heading.startswith("Procedure"):
                continue
            for n, line in lines:
                if line.startswith("```"):
                    fence = not fence; continue
                if fence or line.startswith("|") or line.startswith("#") or line.startswith("Verified against") or not line.strip():
                    continue
                bare = CODE_SPAN_RX.sub("", line)
                if re.search(r"\d", bare) and not cl.TAG_RX.search(line) and not cl.PROVISIONAL_RX.search(line):
                    out.append(Finding(rel, n, "untagged", "a number without a tag: %s" % line.strip()[:70]))
    return out


def rule_generator(root, lua_dir):
    import bus_inventory as bi
    md = os.path.join(root, *HARNESS_MD.split("/"))
    if not os.path.isdir(lua_dir):
        return []
    if not os.path.exists(md):
        return [Finding(HARNESS_MD, 1, "generator", "missing; run python tools/bus_inventory.py")]
    sites = bi.scan(lua_dir)
    if any(s["missing"] for s in sites):
        return [Finding(HARNESS_MD, 1, "generator", "%d TK.register sites lack a complete comment block" % sum(1 for s in sites if s["missing"]))]
    label = os.path.relpath(lua_dir, root).replace("\\", "/")
    if _read(md).replace("\r\n", "\n") != bi.render(sites, label):
        return [Finding(HARNESS_MD, 1, "generator", "drift: not a fresh render; run python tools/bus_inventory.py")]
    return []


def _skill_files(root):
    base = os.path.join(root, *SKILLS_DIR.split("/"))
    return sorted(os.path.join(base, d, "SKILL.md") for d in os.listdir(base) if os.path.exists(os.path.join(base, d, "SKILL.md"))) if os.path.isdir(base) else []


def _bullets(sections, heading):
    for h, lines in sections:
        if h.strip().lower() == heading:
            return [(n, l[2:].strip()) for n, l in lines if l.startswith("- ")]
    return []


def rule_skill(root):
    out = []
    for path in _skill_files(root):
        rel, secs = _rel(path, root), _sections(_read(path))
        pages = [m.group(1) for _, l in _bullets(secs, "read first") for m in [re.search(r"(docs/[A-Za-z0-9_./-]+\.md)", l)] if m]
        rules = set()
        for page in pages:
            p = os.path.join(root, *page.split("/"))
            if os.path.exists(p):
                rules |= {l for _, l in _bullets(_sections(_read(p)), "rules")}
        for n, quoted in _bullets(secs, "rules quoted"):
            if quoted not in rules:
                out.append(Finding(rel, n, "skill", "quoted rule is not verbatim on a Read-first page: %s" % quoted[:70]))
    return out


def rule_example(root):
    out = []
    for path in _md_files(root, ("docs/platform",)):
        rel = _rel(path, root)
        for heading, lines in _sections(_read(path)):
            if not heading.startswith("Worked examples"):
                continue
            for n, line in lines:
                if line.startswith("|") and not re.match(r"^\|\s*:?-", line):
                    cells = [c.strip() for c in line.strip("|").split("|")]
                    if len(cells) >= 2 and cells[0].lower() != "shape":
                        m = FILE_LINES_RX.search(cells[1])
                        if not m or not os.path.exists(os.path.join(root, *m.group(1).split("/"))):
                            out.append(Finding(rel, n, "example", "worked example path does not exist: %s" % cells[1]))
    return out


def fix_tags(root, register=None):
    rows = cl.read_register(register or os.path.join(root, *REGISTER.split("/")))
    by_id = {r["id"]: r for r in rows}
    changed = 0
    for path in _md_files(root, LAYER_DIRS):
        text = _read(path)
        def fix(m):
            items = ["%s%s" % (cid, cl.canonical_suffix(by_id[cid]) if cid in by_id else suffix) for cid, suffix in cl.split_tag(m.group(1))]
            return "[" + ", ".join(items) + "]"
        new = cl.TAG_RX.sub(fix, text)
        if new != text:
            open(path, "w", encoding="utf-8", newline="").write(new); changed += 1
    return changed


def section_map(rows):
    out = collections.defaultdict(list)
    for r in rows:
        for src in [s.strip() for s in r["source"].split(";") if s.strip()]:
            out[src].append(r["id"])
    return dict(out)


def staged_paths(root):
    r = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=root, capture_output=True, text=True)
    return [p.strip() for p in r.stdout.splitlines() if p.strip()]


def check(root=None, register=None, lua_dir=None, register_only=False, partial=False, allow_provisional=False):
    root = root or REPO_ROOT
    reg_path = register or os.path.join(root, *REGISTER.split("/"))
    reg_rel = _rel(reg_path, root)
    try:
        rows = cl.read_register(reg_path)
    except (cl.RegisterError, OSError) as e:
        return [Finding(reg_rel, 1, "schema", str(e))]
    findings = rule_schema(rows, reg_rel) + rule_pointer(rows, root, reg_rel)
    if register_only:
        return findings
    lua = lua_dir or os.path.join(root, *LUA_DIR.split("/"))
    findings += rule_owner(rows, root, partial) + rule_tag(rows, root, allow_provisional) + rule_untagged(root)
    findings += rule_generator(root, lua) + rule_skill(root) + rule_example(root)
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=REPO_ROOT); ap.add_argument("--register"); ap.add_argument("--lua-dir")
    ap.add_argument("--register-only", action="store_true"); ap.add_argument("--partial", action="store_true")
    ap.add_argument("--staged", action="store_true"); ap.add_argument("--allow-provisional", action="store_true")
    ap.add_argument("--fix-tags", action="store_true"); ap.add_argument("--view"); ap.add_argument("--section-map", action="store_true")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root)
    if a.staged and not any(p.startswith(TRIGGERS) for p in staged_paths(root)):
        print("nothing staged under the checker's trigger paths; skipped"); return 0
    if a.fix_tags:
        print("%d files rewritten" % fix_tags(root, a.register))
    if a.view or a.section_map:
        rows = cl.read_register(a.register or os.path.join(root, *REGISTER.split("/")))
        if a.view:
            for r in rows:
                if r["owner"].startswith(a.view.rstrip("/") + "/"):
                    print("\t".join(r[c] for c in cl.COLUMNS))
        if a.section_map:
            for src, ids in sorted(section_map(rows).items()):
                print("%s -> %s" % (src, ", ".join(ids)))
        return 0
    findings = check(root, a.register, a.lua_dir, a.register_only, a.partial, a.allow_provisional)
    for f in sorted(findings, key=lambda f: (f.path, f.line, f.rule)):
        print("%s:%d: %s: %s%s" % (f.path, f.line, f.rule, f.detail, " (warning)" if is_warning(f) else ""))
    n_err = sum(1 for f in findings if not is_warning(f)); n_warn = len(findings) - n_err
    print("%d findings, %d warnings" % (n_err, n_warn))
    return exit_code(findings)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `python -m pytest tools/tests/test_claims_check.py -q` → `8 passed`. A test that fails on a detail string is fixed in the tool's message, not by weakening the assertion, unless the assertion contradicts the rule as the spec states it.

- [ ] **Step 5: Run the whole suite and document**

Run: `python -m pytest tools/tests testing/tests -q 2>&1 | tail -1` → green.

Append to `tools/README.md` `## Reference tooling`:

```markdown
- `claims_check.py` — `python tools/claims_check.py [--register TSV] [--register-only] [--partial]
  [--staged] [--allow-provisional] [--fix-tags] [--view LAYER] [--section-map] [--root DIR]`
  The register checker (spec § The checker). Rules: `schema` (columns, grammars, duplicate ids,
  contiguity from each id sub-block's first id, successors), `pointer` (`run:` folders exist or
  are aliased in `run-aliases.csv`, keys are not in `do-not-cite.csv`, `repo:` paths exist),
  `owner` (each row's owner page carries its tag), `tag` (every tag in `docs/{areas,platform,facts}`
  and the skills resolves and carries the canonical suffix; provisional `[T…]` tags fail),
  `untagged` (warning only: a number without a tag outside fences, tables and `## Procedure`),
  `generator` (`harness-commands.md` is a fresh render), `skill` (every `## Rules quoted` line is
  verbatim on a `## Read first` page), `example` (`## Worked examples` paths exist).
  `--register-only` = schema + pointer (Phase 1; every harvest part is checked this way);
  `--partial` lets `owner` skip pages not yet written (Phases 2–3); `--staged` skips when nothing
  relevant is staged; `--fix-tags` rewrites suffixes from the register. Exit 1 iff a non-warning
  finding. Run it before every commit that touches `docs/`, `.claude/skills/`, `testing/PZTestKit/`,
  `testing/artifacts/`, `testing/experiments/` or `tools/bus_inventory.py`.
```

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git commit -m "tools: claims_check (the register checker)" -- tools/claims_check.py tools/tests/test_claims_check.py tools/README.md
```

---

### Task 10: `do-not-cite.csv`

**Files:**
- Create: `docs/reference/do-not-cite.csv`

**Interfaces:**
- Consumes: `tools/claims_harvest.py do-not-cite` (Task 4).
- Produces: the checker's rule-3 input (Task 9), read by every harvest task's validation step. Columns `run,key,value,why,read_instead`; a prose restriction has `key = *`.

- [ ] **Step 1: Generate**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_harvest.py do-not-cite testing/artifacts/README.md --out docs/reference/do-not-cite.csv && wc -l docs/reference/do-not-cite.csv && cut -d, -f1 docs/reference/do-not-cite.csv | sort | uniq -c
```

Expected: 40–80 rows spread over the runs that carry a **Do not cite** block (the README has 37 such mentions; a run with a block and zero rows in the CSV is a parser miss).

- [ ] **Step 2: Verify by hand against the README**

For every `**Do not cite from …**` marker in `testing/artifacts/README.md` (`grep -n 'Do not cite from' testing/artifacts/README.md`), open the block and confirm: the run id the CSV attributes to it is the run whose section the block sits in (or the run the marker names); every key in the block's table is a row, keys joined with "and" split into one row each; every bullet restriction is a `*` row with its text in `why`. Fix a miss by fixing the parser in `tools/claims_harvest.py` (with a test case for the shape that was missed), never by hand-editing the CSV.

- [ ] **Step 3: Commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git add docs/reference/do-not-cite.csv && git commit -m "Reference: do-not-cite.csv from the artifacts README" -- docs/reference/do-not-cite.csv tools/claims_harvest.py tools/tests/test_claims_harvest.py
```

---

### Task 11: Harvest G1a — the eating pipeline and nutrition core

**Files:**
- Create: `docs/reference/parts/claims-G1a.tsv`, `docs/reference/parts/coverage-G1a.md`

**Interfaces:**
- Consumes: `docs/superpowers/plans/restructure-1-harvest-procedure.md` (read it first; it is binding), `docs/superpowers/plans/restructure-anchors.md` (Task 8), `tools/claimslib.py`, `tools/claims_harvest.py`, `tools/claims_check.py`, `docs/reference/do-not-cite.csv`, `docs/reference/run-aliases.csv`.
- Produces: register rows `#0001–#0200` (contiguous from `#0001`) and the coverage part for `docs/vanilla/eating-pipeline.md` and `docs/vanilla/nutrition-core.md`.

Sources: `docs/vanilla/eating-pipeline.md` (671 lines; 108 evidence rows, about 25 graded paragraphs), `docs/vanilla/nutrition-core.md` (311 lines; 8 rows, about 8 paragraphs, and about 40 numbers in the `Verified on server` bullets). Expected: 110–140 rows.

Special rules for this group:
- The annotated `Eat` transcript (§ the bytecode block with `@offsets`, about lines 53–161) is one `order` row (claim: the order of writes it fixes — fraction rescale, the stat adds, the four nutrition setters, `JustAteFood`, the packet sends, `OnEat`, `UseAndSync`); the prose consequences that rest on it ("nutrition is written before `OnEat` fires and before the item is consumed"; "`JustAteFood` is the only use of `useUtensil`"; "`f0`, not `f`, in the custom-weight write") are separate `mechanism` rows pointing at their own offsets.
- The modifier table (§ Every modifier, 67 rows, 30 of them `C+M`) is not a dataset: one row per modifier, two pointers where the cell has both, the run and key from the cell.
- § MP behaviour rows are owned by `facts/wire-packets.md` (field contracts, measured desyncs) or `platform/mp-model.md` (mechanisms) per the anchor plan and the spec's sync placement, never by `facts/eating-pipeline.md`.
- The wiki-discrepancy table (6 rows) → `contradiction` rows owned by `facts/eating-pipeline.md#walls`.
- `nutrition-core.md` § the `Verified on server` bullets: split into `rate` mechanism rows — the coded gain rate with its `arith.` bound, the ramp-day factor, the sawtooth factor with the 4-of-73 samples note in `bound`, the three-day resolution floor — so a designer reads the bridge between the coded and the measured rate as facts, not as a session story. The headings `Resolved in slice 03` carry facts: harvest the facts, drop the narrative.
- § Inputs for slice 04 (harness/profile inputs, about 64 lines) is process, not a claim about the game: list it in coverage as dropped with that reason.
- Spike S6 readings that `eating-pipeline.md` marks overturned are `superseded` rows whose successor is the current row.

- [ ] **Step 1: Generate the candidates and read the procedure**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_harvest.py candidates docs/vanilla/eating-pipeline.md docs/vanilla/nutrition-core.md --out .superpowers/sdd/restructure-1-register/candidates-G1a.tsv
```

Then read `docs/superpowers/plans/restructure-1-harvest-procedure.md` in full, then the two source files in full.

- [ ] **Step 2: Write the rows and the coverage part** as the procedure's § 2–§ 4 specify, ids from `#0001`.

- [ ] **Step 3: Validate**

Run: `python tools/claims_check.py --register docs/reference/parts/claims-G1a.tsv --register-only` → `0 findings`; `python -m pytest tools/tests -q` green.

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git add docs/reference/parts/claims-G1a.tsv docs/reference/parts/coverage-G1a.md && git commit -m "Harvest: G1a (eating pipeline, nutrition core)" -- docs/reference/parts/claims-G1a.tsv docs/reference/parts/coverage-G1a.md
```

---

### Task 12: Harvest G1b — the food item model

**Files:**
- Create: `docs/reference/parts/claims-G1b.tsv`, `docs/reference/parts/coverage-G1b.md`

**Interfaces:**
- Consumes: as Task 11 (the procedure file, the anchor plan, the three tools, the two CSVs).
- Produces: register rows `#0201–#0450` (contiguous from `#0201`) and the coverage part for `docs/vanilla/food-item-model.md`.

Source: `docs/vanilla/food-item-model.md` (901 lines; 239 evidence rows, about 34 graded paragraphs, 80 fenced lines). Expected: 130–170 rows after the table rule.

Special rules for this group:
- The 114-key script reference (§ the key table, about lines 90–205) is one `table` row (claim: 114 `food.txt`/`drainable.txt` keys, what the loader does with each, read on 42.20.4) plus one row per exception the prose singles out (the dead keys, a key with a measured surprise). Owner `facts/food-item-model.md#script-keys`.
- Aging, fridge/freezer/frozen, spawn-time age, sealed cans, `ReplaceOnRotten`, the rot sandbox options (about lines 219–352) → owner `facts/spoilage.md` anchors; the aging formula block is one `order` row.
- The cook block and evolved-recipe summation (about lines 354–528) → owner `facts/cooking-and-recipes.md` anchors; the cook block is one `order` row.
- The item packets (about lines 615–709): the cached-packet leak mechanism → `platform/mp-model.md`; the per-field table (which getters travel, `offAge`/`offAgeMax`/`isCookable`/`isCustomWeight` never travel) → `facts/wire-packets.md` as one `table` row plus one row per measured desync.
- The 10 wiki-discrepancy rows → `contradiction` rows owned by `facts/food-item-model.md#walls` (or the spoilage page's `#walls` when the fact is a rot fact).
- The thaw-rate open question that names `exp02-20260910-025434` (no artifact folder) → one `open` row, bound `uncommitted: exp02-20260910-025434 …`, owner `facts/spoilage.md#open`.
- Packaging/canned (6 rows) → per the anchor plan (`facts/spoilage.md#sealed` unless the plan says otherwise).

- [ ] **Step 1: Generate the candidates and read the procedure**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_harvest.py candidates docs/vanilla/food-item-model.md --out .superpowers/sdd/restructure-1-register/candidates-G1b.tsv
```

Then read `docs/superpowers/plans/restructure-1-harvest-procedure.md` in full, then the source in full.

- [ ] **Step 2: Write the rows and the coverage part**, ids from `#0201`.

- [ ] **Step 3: Validate**

Run: `python tools/claims_check.py --register docs/reference/parts/claims-G1b.tsv --register-only` → `0 findings`; `python -m pytest tools/tests -q` green.

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git add docs/reference/parts/claims-G1b.tsv docs/reference/parts/coverage-G1b.md && git commit -m "Harvest: G1b (food item model)" -- docs/reference/parts/claims-G1b.tsv docs/reference/parts/coverage-G1b.md
```

---

### Task 13: Harvest G1c — body stats

**Files:**
- Create: `docs/reference/parts/claims-G1c.tsv`, `docs/reference/parts/coverage-G1c.md`

**Interfaces:**
- Consumes: as Task 11.
- Produces: register rows `#0451–#0600` (contiguous from `#0451`) and the coverage part for `docs/vanilla/body-stats.md`.

Source: `docs/vanilla/body-stats.md` (743 lines; 144 evidence rows, about 29 graded paragraphs). Expected: 110–140 rows.

Special rules for this group:
- The five-branch passive burn is one `order` row plus one `mechanism` row per branch constant (each branch has its own offsets) and one `rate` mechanism row per measured fit (run + key), owner `facts/body-and-weight.md#passive-burn`.
- The six `C (arith.)` milestone rows → rows with bound `arith.`.
- The 16-row wiki table → `contradiction` rows owned by `facts/body-and-weight.md#walls`; the 16-row code map is a pointer index, not claims — list it in coverage as `pointer index, no rows`.
- The 13 MP rows → `facts/wire-packets.md` (fields) / `platform/mp-model.md` (mechanism), per the anchor plan.
- The weight bands: the settled inclusive-comparison row (measured edges 100/85/75; the 50 and 65 edges `C-only` because the server nudged the weight — write that in `bound`, from the blockquote "Why 50 and 65 are C, not M"), and the earlier exclusive-band statement as a `superseded` row with the settled row as successor; `summary.r12.allBandsMatch` is on the do-not-cite list — never a pointer, quote its restriction in `bound`.
- The 1.005 idle-burn excess ("tentative reading, n = 1") → bound `n=1 … inference` on the fit row, never a claim of its own.
- Moodle thresholds (HUNGRY/THIRST/FOOD_EATEN) and what they drive → `facts/body-and-weight.md#moodle-thresholds`; every sandbox option on this page → the `#sandbox` anchor.

- [ ] **Step 1: Generate the candidates and read the procedure**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_harvest.py candidates docs/vanilla/body-stats.md --out .superpowers/sdd/restructure-1-register/candidates-G1c.tsv
```

Then read `docs/superpowers/plans/restructure-1-harvest-procedure.md` in full, then the source in full.

- [ ] **Step 2: Write the rows and the coverage part**, ids from `#0451`.

- [ ] **Step 3: Validate**

Run: `python tools/claims_check.py --register docs/reference/parts/claims-G1c.tsv --register-only` → `0 findings`; `python -m pytest tools/tests -q` green.

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git add docs/reference/parts/claims-G1c.tsv docs/reference/parts/coverage-G1c.md && git commit -m "Harvest: G1c (body stats)" -- docs/reference/parts/claims-G1c.tsv docs/reference/parts/coverage-G1c.md
```

---

### Task 14: Harvest G1d — the food and recipe datasets

**Files:**
- Create: `docs/reference/parts/claims-G1d.tsv`, `docs/reference/parts/coverage-G1d.md`

**Interfaces:**
- Consumes: as Task 11.
- Produces: register rows `#0601–#0800` (contiguous from `#0601`) and the coverage part for `docs/vanilla/food-dataset-notes.md` and `docs/vanilla/recipes-dataset-notes.md`.

Sources: `docs/vanilla/food-dataset-notes.md` (383 lines; 55 rows, about 19 paragraphs, half of them `M`), `docs/vanilla/recipes-dataset-notes.md` (533 lines; 113 rows, about 28 paragraphs). Expected: 90–130 rows.

Special rules for this group:
- Per-food and per-recipe values never become rows: the dataset is the pointer (`data:data/food-items.json items[id=…]`). A row exists only where the doc states a value as an example, a control or a measured subject.
- The datasets' fidelity facts are `M` rows about the game, not about the files: the live census (the three counts on two boots), the ten spot checks (one row per check type with `n` in the bound, not ten rows), the three-drink per-litre probe and the per-litre chain, the uses-not-items rule measured on three items, the MakeToast negative result. Owner: the `#dataset-fidelity` anchor of `facts/food-item-model.md` (foods) or `facts/cooking-and-recipes.md` (recipes) per the anchor plan; `reference/datasets.md` links them and owns only `count` rows.
- The 31 craft deltas → one `table` row plus one row per named inconsistency (`open_mac_and_cheese` +2 800, the four corn mills); the evolved join arms and the 3 + 8 `ReplaceOn*` links → `facts/cooking-and-recipes.md` (links to rot → `facts/spoilage.md#replace-on-rotten`).
- The four `kind` buckets and the selection rule, absent-vs-zero, the `nutrition_source` / `nutrition_basis` rule → `count`/`mechanism` rows owned by `reference/datasets.md#columns` with `snapshot <date>` bounds (the date is the scan date the doc states).
- Counts from a dated scan carry `snapshot <date>` as the bound's first token.

- [ ] **Step 1: Generate the candidates and read the procedure**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_harvest.py candidates docs/vanilla/food-dataset-notes.md docs/vanilla/recipes-dataset-notes.md --out .superpowers/sdd/restructure-1-register/candidates-G1d.tsv
```

Then read `docs/superpowers/plans/restructure-1-harvest-procedure.md` in full, then the two sources in full.

- [ ] **Step 2: Write the rows and the coverage part**, ids from `#0601`.

- [ ] **Step 3: Validate**

Run: `python tools/claims_check.py --register docs/reference/parts/claims-G1d.tsv --register-only` → `0 findings`; `python -m pytest tools/tests -q` green.

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git add docs/reference/parts/claims-G1d.tsv docs/reference/parts/coverage-G1d.md && git commit -m "Harvest: G1d (food and recipe datasets)" -- docs/reference/parts/claims-G1d.tsv docs/reference/parts/coverage-G1d.md
```

---

### Task 15: Harvest G2a — mod anatomy and the Lua API

**Files:**
- Create: `docs/reference/parts/claims-G2a.tsv`, `docs/reference/parts/coverage-G2a.md`

**Interfaces:**
- Consumes: as Task 11 (the procedure file is binding; the anchor plan; the three tools; the two CSVs).
- Produces: register rows `#0801–#1000` (contiguous from `#0801`) and the coverage part for `docs/modding/anatomy.md` and `docs/modding/lua-api.md`.

Sources: `docs/modding/anatomy.md` (461 lines; 67 rows, about 18 paragraphs), `docs/modding/lua-api.md` (464 lines; 58 rows, about 8 paragraphs). The slice-12 claims files (`.superpowers/sdd/12-platform-reference/session-1-claims.md` … `session-7-claims.md`) are read for bounds and artifact keys only; `source` never names them (they are gitignored; their content is in these two docs). Expected: 120–160 rows.

Special rules for this group:
- Two merges are named apart: the file-level merge (version dir over `common/`, `LoadDirBase`'s vanilla-first dedupe, translations) is owned by `platform/mod-anatomy.md`; the block-level script merge is `platform/loader-and-scripts.md#per-key-merge` — but that mechanism's rows come from `item-overrides.md` (G2b); here, harvest only what `anatomy.md` states about the file map and the Lua load order (`#file-map`, `#lua-load-order`).
- The "a mod's `server/` file runs in the MP client VM" fact has four homes in the old docs; harvest it once here (from `anatomy.md` § the measured section, three witnesses in `bound`), owner per the anchor plan (`platform/overview.md#two-lua-states` or `platform/lua-platform.md`, whichever the plan names); the guard rule is a separate `rule` row on `platform/lessons.md#rules`.
- `anatomy.md`'s `mod_lint` engine-standing rows (about lines 219–248: `mod-info-place` is a bounded measured statement, `media` is an intent check, `folder-id` is an engine reading) → owner `reference/tools.md#mod-lint`.
- The `versionMin` gate, `getGameVersionIntFromName` ignoring the third component, `loadModAfter/Before` advisory and client-UI only, `incompatible` display-only, the `-nosteam` discovery path, the `x123`/`x123b` mod.info chain (the alias resolves `x123b`) → `platform/mod-anatomy.md` anchors.
- `lua-api.md`: the 28 `TK.ITEM_STATE` keys against `ItemStatsPacket` → one `table` row owned by `facts/wire-packets.md`; the nil-call block (about lines 213–276) → one row per independently falsifiable statement (about ten, two runs); the exposure test and Java-member access rules → `platform/lua-platform.md#java-members`; the 13 curated events with side and cadence → one `table` row plus a row per event whose cadence was measured; "the full event roster lives on the wiki" → a `bound` row on `platform/overview.md#coverage`.
- Every `~:NN` line cite is re-located by content before it becomes a `lua:`/`repo:` pointer with anchor text.

- [ ] **Step 1: Generate the candidates and read the procedure**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_harvest.py candidates docs/modding/anatomy.md docs/modding/lua-api.md --out .superpowers/sdd/restructure-1-register/candidates-G2a.tsv
```

Then read `docs/superpowers/plans/restructure-1-harvest-procedure.md` in full, then the two sources in full.

- [ ] **Step 2: Write the rows and the coverage part**, ids from `#0801`.

- [ ] **Step 3: Validate**

Run: `python tools/claims_check.py --register docs/reference/parts/claims-G2a.tsv --register-only` → `0 findings`; `python -m pytest tools/tests -q` green.

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git add docs/reference/parts/claims-G2a.tsv docs/reference/parts/coverage-G2a.md && git commit -m "Harvest: G2a (mod anatomy, Lua API)" -- docs/reference/parts/claims-G2a.tsv docs/reference/parts/coverage-G2a.md
```

---

### Task 16: Harvest G2b — item overrides, patterns, the modding README

**Files:**
- Create: `docs/reference/parts/claims-G2b.tsv`, `docs/reference/parts/coverage-G2b.md`

**Interfaces:**
- Consumes: as Task 11.
- Produces: register rows `#1001–#1120` (contiguous from `#1001`) and the coverage part for `docs/modding/item-overrides.md`, `docs/modding/patterns.md`, `docs/modding/README.md`.

Sources: `docs/modding/item-overrides.md` (473 lines; 42 rows, about 18 paragraphs), `docs/modding/patterns.md` (587 lines; 12 rows, about 10 paragraphs, the KEEP/FILTER entries — CRLF file), `docs/modding/README.md` (68 lines: the "hard-won platform facts" and two claims marked not re-verified). Expected: 90–120 rows.

Special rules for this group:
- `patterns.md`'s `setWeight` row (about line 280) is at least eight rows: the client discards the weight delta; the three flags are computed on both sides; they agree on the trivial arm; they agree on both non-trivial arms; `incWeightLot` fires from > 400 not 700; `nutrition.set calories -100` is not clamped; `updateWeight` has no timer gate; the "evaluate server-side" consequence as a `C` row with bound `inference`. FILTER 10 (about lines 184–219) splits by subject and direction (`n=2` and `n=1` are different bounds).
- Every KEEP and FILTER entry → a `rule` row (claim = the imperative with its reason clause, present tense) owned by `platform/lessons.md#rules` or `#anti-patterns`, pointing at the mechanism rows' pointers; the measured facts under § Measured MP sync facts → `mechanism` rows owned by `platform/mp-model.md` / `facts/wire-packets.md` per the sync placement.
- The rows graded `M (spike S6)` whose runs are `spike-20260909-143930` / `spike-20260909-144417` (no artifact folder) → `status unverified`, `bound uncommitted: <run-id> …`, owner's `#open` anchor listed in coverage.
- `item-overrides.md`: the per-key merge (`n = 1 item, one build, one key type` — the bound verbatim), the sorted replay by stored path, the same-path drop, the `complete` wrapper install, the modData + `syncItemFields` write, the load order between two mods (`x124`/`x125`), the `x125` do-not-cite sentences about `means` quoted in `bound` → `platform/loader-and-scripts.md` / `platform/lua-platform.md#script-hooks` / `platform/mp-model.md#item-moddata` per the anchor plan; the item pass's own reading (minimal blocks, the record count, the six risks) → `areas/item-pass.md` anchors.
- `README.md`'s two claims marked not re-verified (ResourceLocation ids lowercased; `getFileWriter` extension-limited while `getModFileWriter` is not) → `status unverified`, the second with its measured half (`spikes.md` S4) as the pointer.
- Preserve nothing in the CRLF source: you only read it.

- [ ] **Step 1: Generate the candidates and read the procedure**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_harvest.py candidates docs/modding/item-overrides.md docs/modding/patterns.md docs/modding/README.md --out .superpowers/sdd/restructure-1-register/candidates-G2b.tsv
```

Then read `docs/superpowers/plans/restructure-1-harvest-procedure.md` in full, then the three sources in full.

- [ ] **Step 2: Write the rows and the coverage part**, ids from `#1001`.

- [ ] **Step 3: Validate**

Run: `python tools/claims_check.py --register docs/reference/parts/claims-G2b.tsv --register-only` → `0 findings`; `python -m pytest tools/tests -q` green.

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git add docs/reference/parts/claims-G2b.tsv docs/reference/parts/coverage-G2b.md && git commit -m "Harvest: G2b (item overrides, patterns)" -- docs/reference/parts/claims-G2b.tsv docs/reference/parts/coverage-G2b.md
```

---

### Task 17: Harvest G2c — the wall map and the named experiments

**Files:**
- Create: `docs/reference/parts/claims-G2c.tsv`, `docs/reference/parts/coverage-G2c.md`

**Interfaces:**
- Consumes: as Task 11, plus `docs/reference/experiments.md` (Task 7).
- Produces: register rows `#1121–#1300` (contiguous from `#1121`) and the coverage part for `docs/modding/wall-map.md` and `docs/reference/experiments.md`.

Sources: `docs/modding/wall-map.md` (469 lines: 64 verdict rows, 10 MP-behaviour rows, the 26-row experiment table, the 16-row § Discrepancies table, § How to read this map, § What the library cannot yet measure), `docs/reference/experiments.md` (the full specs). Expected: 160–200 rows.

Special rules for this group:
- Every one of the 64 rows → one `verdict` row: claim = the verdict as a sentence ("A mod cannot add a field to the Java `Nutrition` object: it is a closed 26-member value object …"), `kind verdict`, pointer = the row's `Ev` cell converted (a `C · 13 · <site>` cell is a `jar:` pointer; an `M` cell a `run:` pointer), owner `reference/wall-map.md#<row id in lower case>` (`#a1` … `#j5`), `status open` for the three `UNKNOWN` rows.
- A cell fact (Mechanism, Workaround, Residual risk) becomes its own `mechanism` or `bound` row **only** when the map's `Ev` cell cites the jar or a run directly (slice 13's own reads). A cell fact cited to another doc (`patterns.md KEEP 1`, `anatomy.md § 3`, a vanilla doc) is that doc's row: write it in coverage as `cited to <doc § section>, harvested by G1/G2` so the merge task can cross-check.
- The 26 experiment rows → one `open` row each (claim = the question; owner `areas/open-questions.md#x<n>`; pointer `repo:docs/reference/experiments.md:<line> "<the row's first cell>"`; bound = the cost and owner cells in words). The condensed table in the map and the full spec are the same claim: one row, both sources.
- The § Discrepancies table (previously predicted → now) → one `superseded` row per line (claim = the old prediction; pointer = the plan's seed as the map cites it; `successor` = the verdict row's id).
- § What the library cannot yet measure → `bound` rows owned by `platform/harness.md#walls-and-bounds`; the `text.get` null guard "never fired (untriggered, not confirmed)" is one of them.
- § How to read this map: the evidence bound ("42.20.4 on a dedicated server with one client, one fixture, one admin character; single-player is never claimed") → one `bound` row owned by `platform/overview.md#coverage`; the slice-12 dependency rule → a `bound` row on `reference/wall-map.md#how-to-read`.
- The 10 MP-behaviour rows → `facts/wire-packets.md` / `platform/mp-model.md` per the sync placement, with their two runs as two pointers where the cell names both (`exp03-20260910-045523 r13_mp_regression.clientPolls` for the 0.51 s / 1.42 s reads).

- [ ] **Step 1: Generate the candidates and read the procedure**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_harvest.py candidates docs/modding/wall-map.md --out .superpowers/sdd/restructure-1-register/candidates-G2c.tsv
```

Then read `docs/superpowers/plans/restructure-1-harvest-procedure.md` in full, then the two sources in full.

- [ ] **Step 2: Write the rows and the coverage part**, ids from `#1121`.

- [ ] **Step 3: Validate**

Run: `python tools/claims_check.py --register docs/reference/parts/claims-G2c.tsv --register-only` → `0 findings`; `python -m pytest tools/tests -q` green. Then `grep -c 'reference/wall-map.md#' docs/reference/parts/claims-G2c.tsv` → 64 or more (64 verdicts plus the how-to-read bound).

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git add docs/reference/parts/claims-G2c.tsv docs/reference/parts/coverage-G2c.md && git commit -m "Harvest: G2c (wall map, named experiments)" -- docs/reference/parts/claims-G2c.tsv docs/reference/parts/coverage-G2c.md
```

---

### Task 18: Harvest G3a — the teardowns

**Files:**
- Create: `docs/reference/parts/claims-G3a.tsv`, `docs/reference/parts/coverage-G3a.md`

**Interfaces:**
- Consumes: as Task 11.
- Produces: register rows `#1301–#1550` (contiguous from `#1301`) and the coverage part for the five teardowns.

Sources: `docs/mods-survey/teardowns/autocook.md` (800 lines; 41 rows, 11 paragraphs), `longtermpreservation4220.md` (713; 39, 18), `simplestatus.md` (815; 81, 15), `beyondten.md` (91), `itemquality.md` (106). Expected: 130–170 rows.

Special rules for this group:
- The MP tables (about 100 rows across the three big teardowns) are measurements about the game, not about the mods: per-field measured rows owned by `facts/wire-packets.md` (food and nutrition fields: `offAge` 53 vs 1e9, `isCookable`, `getActualWeight` 0.5 → 0, thirst 0.2 → 0.1 → 0.05, the cooked-thirst halving) or `platform/mp-model.md` (mechanisms: the wipe, the push cadence). The 30-row simpleStatus band table → one `table` row plus the two mechanism sentences it establishes (the client is a staircase that steps when a packet lands while the server is a ramp — a timing reading, not float noise; weight's gap is negative at every post-action snapshot, `updateWeight`'s `GameClient.client` skip measured), owner `facts/wire-packets.md#staircase`. `M per arm` cells → one row per arm when the arms have different keys.
- Engine facts a teardown discovered (the brace-unbalanced script the engine tolerates; the module-qualified recipe lookup rule; the server inventory-item tick ≈ 5 s; the `KahluaTableImpl` type bytes and what the wire drops; the 13-language `overrides` lines a client-only mod's translate tree produces on the server) are `platform/` or `facts/` rows by placement, never `other-mods/` rows.
- What the mod does, techniques worth stealing, pitfalls, compatibility → rows owned by `facts/other-mods/<mod>.md#what-it-does` / `#techniques` / `#pitfalls` / `#compat`; the pointer is `mod:<workshop id>/<tree>/<path>:<line> "<anchor text>"`, tree-qualified (`common`, `42.13`, …) exactly as the teardown cites it; a claim about the mod's MP behaviour on `#mp` cites the `facts/wire-packets.md` rows' pointers, never restates the numbers.
- Client-only mods as a category (simpleStatus 100 % client, the server loads only its translate tree; AutoCook's globals absent server-side) → `platform/mod-anatomy.md#client-only-mods`.
- Every dated correction inside a teardown (six in `longtermpreservation4220.md`) → `superseded` rows.

- [ ] **Step 1: Generate the candidates and read the procedure**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_harvest.py candidates docs/mods-survey/teardowns/autocook.md docs/mods-survey/teardowns/longtermpreservation4220.md docs/mods-survey/teardowns/simplestatus.md docs/mods-survey/teardowns/beyondten.md docs/mods-survey/teardowns/itemquality.md --out .superpowers/sdd/restructure-1-register/candidates-G3a.tsv
```

Then read `docs/superpowers/plans/restructure-1-harvest-procedure.md` in full, then the five sources in full.

- [ ] **Step 2: Write the rows and the coverage part**, ids from `#1301`.

- [ ] **Step 3: Validate**

Run: `python tools/claims_check.py --register docs/reference/parts/claims-G3a.tsv --register-only` → `0 findings`; `python -m pytest tools/tests -q` green.

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git add docs/reference/parts/claims-G3a.tsv docs/reference/parts/coverage-G3a.md && git commit -m "Harvest: G3a (teardowns)" -- docs/reference/parts/claims-G3a.tsv docs/reference/parts/coverage-G3a.md
```

---

### Task 19: Harvest G3b — the mod catalog

**Files:**
- Create: `docs/reference/parts/claims-G3b.tsv`, `docs/reference/parts/coverage-G3b.md`

**Interfaces:**
- Consumes: as Task 11.
- Produces: register rows `#1551–#1700` (contiguous from `#1551`) and the coverage part for `docs/mods-survey/nutrition-mods.md`, `docs/mods-survey/approved-modlist.md`, `docs/mods-survey/README.md`.

Sources: `docs/mods-survey/nutrition-mods.md` (711 lines; 109 rows, about 30 paragraphs), `docs/mods-survey/approved-modlist.md` (129 lines), `docs/mods-survey/README.md` (90 lines). Expected: 70–100 rows.

Special rules for this group:
- The sweep and status tables (87 rows) and the 24-row API-surface table → `table` rows (claim = what the table is, its row count, the sweep stamp `snapshot 2026-09-10 17:47` or the doc's own date) plus one row per exception the prose singles out; owner `facts/other-mods/catalog.md#sweep` / `#status` / `#api-surface`.
- Corpus-level facts (the event census; 39 mods share `OnPlayerUpdate`; the Girth stack's 228 command sites; the 230-mod counts; `loadstring` zero; the one `Base.Rope` collision; the `media_at` flag — 177 of 230 list a `common/media`) → `count` or `mechanism` rows owned by `facts/other-mods/catalog.md#corpus-facts`, every count dated in `bound`.
- The catalog's per-mod verdicts about nutrition handling (which mods write `Nutrition`, which read it, which ship server-side code) → rows owned by the catalog page; a claim that is really about the game (a mod proves a route exists) is a `platform/` or `facts/` row with the mod as the pointer's tree.
- `approved-modlist.md`'s top-12 events → one `count` row; the README's process text is dropped as narrative.

- [ ] **Step 1: Generate the candidates and read the procedure**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_harvest.py candidates docs/mods-survey/nutrition-mods.md docs/mods-survey/approved-modlist.md docs/mods-survey/README.md --out .superpowers/sdd/restructure-1-register/candidates-G3b.tsv
```

Then read `docs/superpowers/plans/restructure-1-harvest-procedure.md` in full, then the three sources in full.

- [ ] **Step 2: Write the rows and the coverage part**, ids from `#1551`.

- [ ] **Step 3: Validate**

Run: `python tools/claims_check.py --register docs/reference/parts/claims-G3b.tsv --register-only` → `0 findings`; `python -m pytest tools/tests -q` green.

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git add docs/reference/parts/claims-G3b.tsv docs/reference/parts/coverage-G3b.md && git commit -m "Harvest: G3b (mod catalog)" -- docs/reference/parts/claims-G3b.tsv docs/reference/parts/coverage-G3b.md
```

---

### Task 20: Harvest G4 — testing, data, tools, ledgers and the working reads

**Files:**
- Create: `docs/reference/parts/claims-G4.tsv`, `docs/reference/parts/coverage-G4.md`

**Interfaces:**
- Consumes: as Task 11, plus the committed parts `docs/reference/parts/claims-G2a.tsv`, `claims-G2b.tsv`, `claims-G2c.tsv` (this task runs after Tasks 15–17 are committed: a superseded bullet's `successor` is one of their ids).
- Produces: register rows `#1701–#2000` (contiguous from `#1701`) and the coverage part for the sources below.

Sources: `docs/testing/README.md` (907 lines, CRLF; no evidence tables — about 120 bullets, of which about 40 are reading rules about the bus), `docs/testing/profiles.md` (661; 53 rows, 10 paragraphs), `docs/testing/pipeline-design.md` (242), `docs/testing/spikes.md` (340), `data/README.md` (986; 15 rows, 9 paragraphs), `tools/README.md` (the `mod_lint` rules and the scanner conventions), `CLAUDE.md` § 8 and § 10, `docs/decisions.md` (bound rows only), `docs/reference/jar-method-notes.md` (tool rows), `.superpowers/sdd/wave-4/not-settled.md`, `.superpowers/sdd/13-wall-map/slice-12-bounds.md`, `.superpowers/sdd/14-feasibility-notes/slice-13-bounds.md`. Expected: 220–300 rows.

Special rules for this group:
- The bus reading rules (an empty list arrives as `{}`; `count` is not a partition; `resolved` names the subject that answered; `grep_file`'s `limit` is a BREAK and a client prints `2 × n`; `server_errors` is a classifier's output; a client-side `[[verify]]` gate never runs when the client hangs; `[client] timeout`; a client-spawned item trips a server NPE; the `-debug` client parks on the first unguarded raise; the cadence ceiling; `WITNESS_MAX = 32`; the `text.get` four shapes; `lua.global`'s walk rules; `recipes.craft`'s three outcomes) → `rule` and `mechanism` rows owned by `platform/harness.md#reading-a-reply`, `#probes`, `#cadence`, `#driven-client` per the anchor plan; the `pzt` commands and the profile schema (the fifteen keys) → `table` rows plus a row per key with a measured behaviour (`profiles.md`'s 53 rows).
- The process model (server args and ini keys, `+connect`, `-cachedir`, `-nosteam` discovery, RCON and the commands proven over it, the admin command classes, `default.txt` and the `reset-mods-42_00.txt` marker, the join-time Lua reset, `debug-options.ini`, `ServerList.db`) → `platform/overview.md#process-model`; the dev loop (`reloadlua` re-runs one file with globals intact; `reloadLuaFile` needs an absolute path; `reloadalllua` throws on a dedicated server; a reloaded file re-`Add`s its handlers; file IO limits; no JSON library) → `platform/lua-platform.md#reload` / `#file-io`.
- `tools/README.md`: the nine `mod_lint` rules with their engine standing, `food_scan.py`'s parser conventions, `workshop_search.py`'s three row states → `reference/tools.md#mod-lint` / `#food-scan` / `#workshop-search` (`tool` rows, `repo:` pointers with anchor text).
- `data/README.md`: the column semantics (`nutrition_basis`, the per-litre join, `*_per_container`), the `media_at` caveat, the 15 evidence rows → `reference/datasets.md#columns` / `#mod-inventory` with `snapshot <date>` bounds; per-item values never.
- `CLAUDE.md` § 8: the platform gotchas (`-debug` parks; the corpus drifts, date every count) → `rule` rows on `platform/lessons.md`; the repository gotchas (cwd reset, heredocs, CRLF, the stray client) are not claims — dropped, with the reason. § 10's headlines are duplicates of docs/modding rows: no new rows; list each as `duplicate of <doc § section>` in coverage.
- `docs/decisions.md`: only rulings that bound a claim become `bound` rows (artifacts older than `291f977` render floats at `%.6f`, so no bit-level claim may rest on them; exclusion sets are per scope; the CSV carries no stamp row). Everything else is process: dropped.
- `jar-method-notes.md` → `tool` rows (`grep` is a byte scan over ~23.7k class entries; `methods` lists every declared method regardless of access; `refs` is not a reverse-caller query; inner classes need `$` escaped; `dump` on a large class is slow) with `tool:pz-b42/tools/pzdis.py:<line>` pointers, owner `platform/jar-research.md#method`.
- `not-settled.md` and the two bounds lists: a bullet is imported as a `bound` row only where the wall map or a slice-12 doc does not already carry its successor; a superseded bullet becomes a `superseded` row whose `successor` is the G2 row that settled it (look it up in the committed G2 parts by claim text; if none matches, the bullet is not superseded — import it as a `bound` row).
- `docs/testing/README.md` and `docs/decisions.md` are CRLF: read only.

- [ ] **Step 1: Generate the candidates and read the procedure**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_harvest.py candidates docs/testing/README.md docs/testing/profiles.md docs/testing/pipeline-design.md docs/testing/spikes.md data/README.md tools/README.md CLAUDE.md docs/reference/jar-method-notes.md --out .superpowers/sdd/restructure-1-register/candidates-G4.tsv
```

The candidates file under-counts this group (most of its claims are bullets without a grade mark): the source files, read in full, are the checklist; the coverage part accounts for every section anyway.

Then read `docs/superpowers/plans/restructure-1-harvest-procedure.md` in full, then every source in full, then the three G2 parts.

- [ ] **Step 2: Write the rows and the coverage part**, ids from `#1701`.

- [ ] **Step 3: Validate**

Run: `python tools/claims_check.py --register docs/reference/parts/claims-G4.tsv --register-only` → `0 findings`; `python -m pytest tools/tests -q` green.

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git add docs/reference/parts/claims-G4.tsv docs/reference/parts/coverage-G4.md && git commit -m "Harvest: G4 (testing, data, tools, ledgers, working reads)" -- docs/reference/parts/claims-G4.tsv docs/reference/parts/coverage-G4.md
```

---

### Task 21: Merge the parts into the register and the coverage table

**Files:**
- Create: `docs/reference/claims.tsv`, `docs/reference/claims-coverage.md`
- Modify: `docs/superpowers/plans/restructure-anchors.md` (the proposed anchors folded in)
- Delete: `docs/reference/parts/` (all nine `claims-*.tsv` and nine `coverage-*.md`)

**Interfaces:**
- Consumes: the nine committed parts (Tasks 11–20), `tools/claims_harvest.py merge`, `tools/claims_check.py`.
- Produces: the register every later phase reads; the coverage table that is acceptance check 7's evidence and the `old section -> ids` map for the wall-map rewrite (Phase 4) and the page writers (Phases 2–3).

- [ ] **Step 1: Merge**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_harvest.py merge && python tools/claims_check.py --register-only && wc -l docs/reference/claims.tsv
```

Expected: `N rows -> docs/reference/claims.tsv; coverage -> docs/reference/claims-coverage.md`, then `0 findings` (a duplicate id across parts fails the merge itself; a contiguity gap fails the check — both mean a harvest part is wrong and go back to that part's task as a fix round, never a hand edit of the merged file). N is expected between 1,000 and 1,500.

- [ ] **Step 2: Resolve cross-group duplicates**

The G2c coverage part lists cell facts as `cited to <doc § section>, harvested by G1/G2`, and the G4 part lists `duplicate of <doc § section>` items. For each, confirm with `python tools/claims_check.py --section-map | grep '<section>'` that the named section has rows. A claim that was harvested twice (the same statement in two parts) is never deleted — ids are never reused and a deletion would open a gap: keep the lower id, set the other row's `status` to `superseded` and its `successor` to the kept id, and append the superseded row's `source` to the kept row's `source`. Record every such pair in the coverage file under a new `## Cross-group duplicates` section at the end (the merge output is regenerated, so write them into the G-part text of the coverage file after merging, not into the parts).

- [ ] **Step 3: Fold the proposed anchors into the anchor plan**

For every `## Anchors proposed` list in `claims-coverage.md`, add the anchor under its page section in `docs/superpowers/plans/restructure-anchors.md` (same line shape; merge two proposals of the same slug into one line). Then confirm every `owner` in the register names an anchor the plan lists:

```bash
cd /c/Users/Angus/repos/project_zomboid && cut -f10 docs/reference/claims.tsv | tail -n +2 | sort -u > /tmp/owners.txt && python - <<'PY'
import re
plan=open("docs/superpowers/plans/restructure-anchors.md",encoding="utf-8").read()
have=set()
page=None
for line in plan.splitlines():
    if line.startswith("## "): page=line[3:].strip()
    m=re.match(r"- `#([a-z0-9-]+)`",line)
    if m and page: have.add(page+"#"+m.group(1))
missing=[o for o in open("/tmp/owners.txt").read().split() if o and o not in have]
print(len(missing),"owners without an anchor line"); print("\n".join(missing[:40]))
PY
```

Expected: `0 owners without an anchor line`. Fix by adding the anchor line (never by changing a row's owner to something the harvester did not intend — if an owner is plainly wrong, that is a fix round for the part).

- [ ] **Step 4: Sanity counts**

Read `## Totals` in `claims-coverage.md`: `verdict` = 64; `open` ≥ 26; `contradiction` about 32; `table` ≥ 10; `unverified` ≥ 16 (one per run id with no artifact, at least); `superseded` ≥ 20 (the dated-correction sites plus the § Discrepancies rows plus cross-group duplicates); no `block` outside `G1a…G4`; no `source` cell contains `.superpowers/` (`grep -c '\.superpowers/' docs/reference/claims.tsv` → 0). A count far outside these bands is a finding to explain in the report, not to fix silently.

- [ ] **Step 5: Delete the parts and commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git rm -q -r docs/reference/parts && python tools/claims_check.py --register-only && python -m pytest tools/tests testing/tests -q 2>&1 | tail -1 && git add docs/reference/claims.tsv docs/reference/claims-coverage.md docs/superpowers/plans/restructure-anchors.md && git commit -m "Register: claims.tsv merged from the nine harvest parts; coverage table; anchor plan folded" -- docs/reference/claims.tsv docs/reference/claims-coverage.md docs/superpowers/plans/restructure-anchors.md docs/reference/parts
```

Expected: `0 findings`, tests green, one commit that adds two files, modifies one and deletes eighteen.

The reviewer of this task samples twenty rows across groups against their sources (as the procedure's § 8 says) and checks: the totals, the cross-group duplicate handling, every owner has an anchor, no `.superpowers/` source, the coverage file accounts for every source section of every old doc (compare its `### <file>` headings with the 23 source files).

---

### Task 22: The acceptance run (live)

**Files:**
- Modify: `testing/experiments/_template.py` (the `ACCEPTANCE_RUN` constant only)

**Interfaces:**
- Consumes: the harness comment commit (Task 6), `docs/reference/harness-commands.md`, `testing/profiles/mod-under-test.toml`, `pzt`.
- Produces: proof that the commented harness boots and answers on both sides; the run id recorded in the SDD ledger and in the template.

This is the one game boot of the plan. One live session at a time, program-wide: the controller confirms nothing else is running before dispatching. A stray `ProjectZomboid64.exe` predating the session is the user's own client — never kill it.

- [ ] **Step 1: Doctor**

Run: `cd /c/Users/Angus/repos/project_zomboid && python testing/pzt doctor`
Expected: every check clean (no java up, ports free, fixture matched). A dirty doctor stops the task: report `BLOCKED` with the doctor output; never kill a process to make it clean.

- [ ] **Step 2: Run**

Run: `cd /c/Users/Angus/repos/project_zomboid && python testing/pzt run --profile mod-under-test --hold 5 2>&1 | tail -40`
Expected: exit 0; the two `[[verify]]` probes (`trait.check` on the server and on the client, expecting `"keenPerceptionLoaded": true`) pass; the run directory `testing/runs/<run-id>/` exists. Record `<run-id>`.

If the run fails: read the server console and the client console under `testing/runs/<run-id>/` for `tried to call nil`, `stack traceback` or a parse error naming a `PZTestKit_*.lua` file; run `python tools/luabalance.py` on the six harness files; report `FAILED` with the excerpt. Never re-run to make it pass without a fix, and never fix anything but a comment line in the harness (a non-comment change is outside this plan — report and stop).

- [ ] **Step 3: Prove the generated table covers the probes**

```bash
cd /c/Users/Angus/repos/project_zomboid && grep -c '`trait.check`' docs/reference/harness-commands.md && python tools/bus_inventory.py --check
```

Expected: at least 1, and `in sync`.

- [ ] **Step 4: Record the run id in the template and commit**

In `testing/experiments/_template.py` set `ACCEPTANCE_RUN = "<run-id>"` (the id from Step 2). Then:

```bash
cd /c/Users/Angus/repos/project_zomboid && python -m pytest testing/tests/test_template.py -q && git commit -m "Template: acceptance run id" -- testing/experiments/_template.py
```

No artifact is committed: an acceptance run is provenance, not evidence (`CLAUDE.md` § 6). The report names the run id, the wall time, and the two probe acks verbatim.

---

### Task 23: Close (controller)

**Files:**
- Modify: `CLAUDE.md` § 3, § 4, § 6
- Modify: the memory file `C:\Users\Angus\.claude\projects\C--Users-Angus\memory\pz-nutrition-mod-project.md` and its index line in `MEMORY.md`

**Interfaces:**
- Produces: the resume point for Phase 2 (a plan to be written with `superpowers:writing-plans` from the spec and the register).

- [ ] **Step 1: Gates**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/doc_lint.py docs/mods-survey docs/modding && python tools/doc_lint.py docs/vanilla docs/modding docs/testing references docs/mods-survey/nutrition-mods.md && python tools/claims_check.py --register-only && python tools/bus_inventory.py --check && python -m pytest tools/tests testing/tests -q 2>&1 | tail -1 && git status --short | wc -l
```

Expected: both lints 0, `0 findings`, `in sync`, tests green (283 plus the new tests; write the number down), a clean tree.

- [ ] **Step 2: `CLAUDE.md`**

§ 3: append one paragraph — "Restructure Phase 1 closed <date> (`<first commit>..<last commit>`): `docs/reference/claims.tsv` (<N> rows: <kind counts>), `claims-coverage.md`, `do-not-cite.csv`, `run-aliases.csv`, `experiments.md`, `jar-method-notes.md`, `harness-commands.md` (generated; 64 sites); `tools/{claimslib,claims_harvest,claims_check,bus_inventory,luabalance}.py`; the driver template; the anchor plan `docs/superpowers/plans/restructure-anchors.md`; acceptance run `<run-id>`." § 4: "Next: write the Phase 2 plan (`docs/superpowers/plans/restructure-2-platform-facts.md`) with `superpowers:writing-plans` from the spec § Execution Phase 2, the anchor plan and `claims_check.py --view platform` / `--view facts`; then execute it with SDD." § 6: add to the gates: `python tools/claims_check.py --staged` before every commit that touches `docs/`, `.claude/skills/`, `testing/PZTestKit/`, `testing/artifacts/`, `testing/experiments/` or `tools/bus_inventory.py` (`--register-only` until the first page exists); `python tools/bus_inventory.py --check` after any harness edit.

- [ ] **Step 3: Commit, push, memory**

```bash
cd /c/Users/Angus/repos/project_zomboid && git commit -m "Restructure 1: close" -- CLAUDE.md && git push origin main && git push origin research-program-v1 && git log --oneline -1 && git ls-remote --tags origin | grep research-program-v1
```

Then update the memory file's status paragraph (Phase 1 closed; the counts; NEXT = the Phase 2 plan) and the `MEMORY.md` index line.

---

## What the whole-branch review checks

The final reviewer (the most capable model available) reads the spec § Execution Phase 0 and Phase 1 and § Acceptance, then verifies on the branch:

1. The tag `research-program-v1` exists and points at the program-close commit; `CLAUDE.md` § 3/§ 4 describe the restructure, not slice 14.
2. `docs/reference/experiments.md` and `jar-method-notes.md` are verbatim moves (diff against the gitignored originals on this machine); `run-aliases.csv` names `x123b`.
3. `tools/luabalance.py` is byte-identical to the gitignored original; every new tool has tests and a `tools/README.md` entry; `python -m pytest tools/tests testing/tests -q` is green at 283 + the new tests.
4. The harness diff is comments only (`git diff research-program-v1..HEAD -- testing/PZTestKit | grep '^[-+]' | grep -v '^[-+][-+]' | grep -v '^+\s*--'` prints nothing); 64 sites carry complete blocks; `harness-commands.md` is a fresh render.
5. `claims.tsv`: `--register-only` clean; the totals in the bands of Task 21 Step 4; twenty sampled rows across groups are faithful to their sources (claim, numbers, pointer, bound, kind, owner); every `superseded` row has a live successor; every `unverified` row names its reason in `bound`; no `.superpowers/` source; every owner has an anchor in the anchor plan.
6. `claims-coverage.md` accounts for every section of the 23 source files (its `### <file>` headings cover the list in the spec's harvest sources) — the Phase 1 half of acceptance check 7.
7. The acceptance run id is recorded in the ledger and the template; no artifact was added under `testing/artifacts/`.
8. Nothing under `docs/vanilla`, `docs/modding`, `docs/mods-survey`, `docs/testing`, `docs/progress.md` or `docs/decisions.md` changed (the cut is Phase 4).
