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

IDIOM_DOC = """# Eating pipeline

## Writes

The bar moves +95 (M, `exp01-20260910-000351`).

No nutrient write (`Eat @235–@251 L5774–L5776`, C).

The run wrote it back (`exp01-20260910-003929`, M), so the server owns it.

The same route holds at 1 Hz (C, 2026-09-10) and on the second boot (M, same run).

Plain prose with no grade at all, a (parenthetical, aside) and an (X, Y) pair.
"""

def test_candidates_inline_grade_idioms():
    """A grade letter set off by a comma inside a parenthesis is a grade: `(M, …)` and `(…, C)`.

    The qualifier after the comma is free text in this repo — `(C, 2026-09-10)`, `(C, jar)`,
    `(M, same run)` — so the rule deliberately does not require a run id or a backtick there;
    demanding one drops 14 genuine graded lines in the harvest files, every one of the eight in
    `docs/mods-survey/teardowns/simplestatus.md` among them. The cost of the looser rule is that
    a non-grade `(M, the mod)` would also match, which is the right trade for a checklist: an
    extra candidate is dropped by the harvester, a missed grade silently under-grades a row.
    A letter that is not C/M/W never matches, so `(X, Y)` and `(parenthetical, aside)` do not.
    """
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "eating.md", IDIOM_DOC)
        rows = ch.candidates([p])
        assert [r["ev"] for r in rows] == ["(M,", ", C)", ", M)", "(C,"]
        assert [r["grades"] for r in rows] == ["M", "C", "M", "C"]
        assert all(r["kind_hint"] == "paragraph" and r["section"] == "Writes" for r in rows)
        assert rows[0]["run_ids"] == "exp01-20260910-000351"

def test_rel_survives_a_path_on_another_drive():
    """`os.path.relpath` raises across Windows drives; a doc off the repo's drive must not crash.

    On POSIX the same string is simply not absolute, so it takes the relative branch and the
    answer is identical — the assertion holds on both platforms.
    """
    assert ch._rel("docs\\vanilla\\body-stats.md") == "docs/vanilla/body-stats.md"
    assert ch._rel(os.path.join(ch.REPO_ROOT, "docs", "vanilla", "x.md")) == "docs/vanilla/x.md"
    other = ("E:" if os.path.splitdrive(ch.REPO_ROOT)[0].upper() == "D:" else "D:") + "\\tmp\\doc.md"
    assert ch._rel(other) == other.replace("\\", "/")

PROSE_README = """# Artifacts

#### `exp09-20260910-101010` — probe.json

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1`.** One session, one fixture. |
| snapshots[].client.census | `{}` | A driver normalisation; read `keyCount` instead. |
"""

def test_do_not_cite_prose_key_cell_is_a_star():
    """A Key cell with no key is a restriction on the whole file, not a key named after prose."""
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "README.md", PROSE_README)
        rows = ch.do_not_cite(p)
        assert [r["key"] for r in rows] == ["*", "snapshots[].client.census"]
        assert rows[0]["why"] == "everything measured here, as a population — **`n = 1`.** One session, one fixture."
        assert rows[1]["read_instead"] == "read `keyCount` instead"

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
