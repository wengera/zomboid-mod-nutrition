# Restructure 2 — `platform/` and `facts/` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write the twenty-one `docs/platform/` and `docs/facts/` pages from the claims register, under the page contract, so every register row owned by those pages is stated once with its tag and the checker is green per page.

**Architecture:** Two small tools first — `tools/claims_delta.py` (the controller applies a page task's delta file to the register and rewrites the page's provisional tags) and `tools/page_lint.py` (the page contract as a checkable rule set) — then the pages, one task per page, written from `claims_check.py --view <page>` and the old source docs, on disjoint files so implementers run in parallel; deltas applied by the controller between a report and its review; `platform/overview.md` last, from the finished anchors; then the close. The binding page procedure is `docs/superpowers/plans/restructure-2-page-procedure.md`.

**Tech Stack:** Python 3.13 (`tools/`, `pytest`), Markdown pages, the claims register `docs/reference/claims.tsv` (`tools/claimslib.py`), `tools/claims_check.py`.

**Spec:** `docs/superpowers/specs/2026-09-17-reference-restructure-design.md` — § The target tree (the tree, the placement rule, the sync placement, the hard cases), § The claims register (Deltas in Phases 2 and 3), § The checker and the generator (the tag grammar), § The page contract, § Execution (Phase 2), § Acceptance.

## Global Constraints

- The page contract (spec § The page contract) binds every page: the stamp line `Verified against 42.20.4 (b0bbce05d5) · <date> · scope: <one line>`; the sections in the contract's order; `## Rules` on `platform/`, `## Key facts` on `facts/`; `## Walls and bounds` ends with a `Not covered:` line; `## Open` carries open rows with `-> X<N>` and the decisions the design must take, no recommendation.
- Writing rules, verbatim from the spec: "present tense, current truth only — no 'previously', 'corrected', 'resolved in', 'the review found', no dates except the stamp and dated counts; every number outside a code block carries a tag; the number appears only on the owner page (other pages link); no run narratives (a session is cited, never described); bounds stated as facts, not as caveats about the process; an inference is written as one". Length 150–400 lines of prose; `harness.md`, `mod-anatomy.md`, `lua-platform.md` and `mp-model.md` may run to 500 or split.
- Tag grammar: a writer types `[#0417]`; `--fix-tags` appends the canonical suffix; several ids `[#0417/M, #0512]`; no other citation form appears in the three layers; a run id in prose only inside a sentence that also carries a tag whose pointer names that run.
- Placement rule: a mechanism goes in `platform/` if it would hold for a weapon mod or a UI mod; in `facts/` if it is a measured property of the food, body or nutrition systems. A fact lives on one page (its `owner`); other pages cite the tag and never restate the number. Sync placement: `platform/mp-model.md` owns the packet mechanisms, `facts/wire-packets.md` the field contracts. The hard cases of spec § The target tree are decided as written there.
- Implementers never edit `docs/reference/claims.tsv`: a row the page needs, retargets, splits or re-statuses is a delta (`task-N-delta.tsv`, procedure § 6) the controller applies with `tools/claims_delta.py` in a `Register: task N delta` commit before the review. The restructure mints no new measurements: an `add` needs evidence the old doc already states.
- Gates before every page commit: `python tools/claims_check.py --partial --allow-provisional` → `0 findings` (rule 4 warnings aimed at 0), then `--fix-tags`; `python tools/page_lint.py <page> --partial` → `0 findings`. Gates before every tool commit: `python -m pytest tools/tests testing/tests -q` green (349 at the start of this plan).
- No game boot in this plan; the install `D:\SteamLibrary\steamapps\common\ProjectZomboid` and the workshop folder `D:\SteamLibrary\steamapps\workshop\content\108600` are read-only; no edit to the harness, drivers, probe mods, datasets, artifacts, the old docs (`docs/vanilla`, `docs/modding`, `docs/mods-survey`, `docs/testing`) or the anchor plan by an implementer.
- Commits: pathspec (`git add <files> && git commit -m "…" -- <files>`), succinct subjects, no Claude attribution, never `--amend`, no push (the controller pushes at the close). Implementers only on disjoint files; Opus for every implementer and reviewer; the Bash tool's cwd resets between calls (`cd /c/Users/Angus/repos/project_zomboid` first); Windows Python takes `C:/Users/...` paths; long files through the Write tool.
- Out of scope here (later plans): the `areas/` pages, the skills, the roots, `reference/datasets.md` and `reference/tools.md`, the wiki-mirror contradiction table, the wall-map and artifacts moves, the cut.

## Execution order

Task 1 → Task 2 (both touch `tools/README.md` and `tools/tests/`) → Tasks 3–22 in waves of up to seven parallel implementers on disjoint page files (facts first, then the mod pages, then platform) → Task 23 (`overview.md`, after every other page exists) → Task 24 (the close, controller).

## File structure

| path | responsibility |
|---|---|
| `tools/claims_delta.py`, `tools/tests/test_claims_delta.py` | apply a delta file: mint ids for `add` rows, supersede a `split` parent, retarget an owner, change a status; rewrite the page's provisional tags; never delete |
| `tools/claims_check.py` (`--view`) | `--view <layer>/<page>.md` prints one page's rows (today only a layer) |
| `tools/page_lint.py`, `tools/tests/test_page_lint.py` | the page contract as rules: stamp, sections, anchors against the register, rule-line shape, the closing `Not covered:` line, narrative markers, the prose cap, worked-example paths, links |
| `tools/README.md` | one entry per new tool under § Reference tooling |
| `docs/platform/*.md` (8), `docs/facts/*.md` (7), `docs/facts/other-mods/*.md` (6) | the pages, one task each |
| `.superpowers/sdd/restructure-2-platform-facts/task-N-delta.tsv` | a task's delta file (gitignored workspace) |
| `CLAUDE.md` § 3, § 4, § 6; the memory file | the close |

---

### Task 1: `tools/claims_delta.py` and `claims_check.py --view <page>`

**Files:**
- Create: `tools/claims_delta.py`, `tools/tests/test_claims_delta.py`
- Modify: `tools/claims_check.py` (the `--view` branch in `main`, about line 480), `tools/tests/test_claims_check.py` (one test), `tools/README.md` § Reference tooling (one entry, plus the `--view` sentence of the `claims_check.py` entry)

**Interfaces:**
- Consumes: `claimslib` — `COLUMNS`, `STATUSES`, `OWNER_RX`, `read_register`, `write_register`, `validate_row`, `id_int`, `id_str`, `is_provisional`, `find_provisional`, `split_tag`, `canonical_suffix`, `TAG_RX`, `BRACKET_RX`.
- Produces: `python tools/claims_delta.py apply <delta.tsv> --pages <page.md> [...] [--register TSV] [--dry-run]` — prints one line per change (`T7.1 -> #2040`, `#0600 superseded -> #2041, #2042`, `#0417 owner a -> b`, `#0512 status -> open`), then `pages rewritten: <paths>` and a `WARNING: provisional tags left on <page>: T7.9` line for any provisional tag the delta did not cover; exit 1 and no write on any invalid delta. `python tools/claims_check.py --view facts/spoilage.md` prints the rows whose owner starts with `facts/spoilage.md#`.

- [ ] **Step 1: Write the failing tests**

`tools/tests/test_claims_delta.py`:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import claimslib as cl
import claims_delta as cd
import pytest

HEADER = "\t".join(cd.DELTA_COLUMNS)


def _register(tmp_path):
    rows = [
        {"id": "#0001", "claim": "One.", "grade": "C", "pointer": "jar:A.b @1 L2", "bound": "", "status": "settled",
         "successor": "", "kind": "mechanism", "source": "docs/vanilla/x.md § Y", "owner": "facts/x.md#a"},
        {"id": "#0002", "claim": "Two.", "grade": "M", "pointer": "run:exp01-20260910-003929 f.json k", "bound": "n=1",
         "status": "settled", "successor": "", "kind": "mechanism", "source": "docs/vanilla/x.md § Y", "owner": "facts/x.md#b"},
        {"id": "#0003", "claim": "Three.", "grade": "C", "pointer": "jar:A.c @1 L3", "bound": "", "status": "settled",
         "successor": "", "kind": "mechanism", "source": "docs/vanilla/x.md § Z", "owner": "facts/x.md#c"},
    ]
    p = tmp_path / "claims.tsv"
    cl.write_register(str(p), rows)
    return str(p)


def _delta(tmp_path, lines):
    p = tmp_path / "delta.tsv"
    p.write_text(HEADER + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


def _page(tmp_path, text):
    p = tmp_path / "x.md"
    p.write_text(text, encoding="utf-8")
    return str(p)


def _add(pid, claim="Added.", owner="facts/x.md#a", grade="C", pointer="jar:A.d @4 L5", bound="", status="settled", kind="mechanism"):
    return "\t".join(["add", pid, claim, grade, pointer, bound, status, "", kind, "docs/vanilla/x.md § Y", owner, "why"])


def test_add_mints_next_id_and_rewrites_the_provisional_tag(tmp_path):
    reg = _register(tmp_path)
    page = _page(tmp_path, "Text [T7.1] and [#0002/M/n=1, T7.1].\n")
    changes, pages = cd.apply(_delta(tmp_path, [_add("T7.1")]), [page], register=reg)
    assert changes == ["T7.1 -> #0004"] and pages == [page]
    rows = cl.read_register(reg)
    assert rows[-1]["id"] == "#0004" and rows[-1]["claim"] == "Added."
    assert open(page, encoding="utf-8").read() == "Text [#0004] and [#0002/M/n=1, #0004].\n"


def test_add_gets_the_canonical_suffix(tmp_path):
    reg = _register(tmp_path)
    page = _page(tmp_path, "Text [T7.1].\n")
    cd.apply(_delta(tmp_path, [_add("T7.1", grade="M", pointer="run:exp01-20260910-003929 f.json k", bound="n=1", status="open")]), [page], register=reg)
    assert open(page, encoding="utf-8").read() == "Text [#0004/M/n=1/open].\n"


def test_split_supersedes_the_parent_and_rewrites_its_tag(tmp_path):
    reg = _register(tmp_path)
    page = _page(tmp_path, "Parent [#0003]. Kids [T7.1] [T7.2].\n")
    lines = ["\t".join(["split", "#0003", "", "", "", "", "", "", "", "", "", "two claims"]), _add("T7.1", "Three a."), _add("T7.2", "Three b.")]
    changes, _ = cd.apply(_delta(tmp_path, lines), [page], register=reg)
    rows = {r["id"]: r for r in cl.read_register(reg)}
    assert rows["#0003"]["status"] == "superseded" and rows["#0003"]["successor"] == "#0004, #0005"
    assert open(page, encoding="utf-8").read() == "Parent [#0004, #0005]. Kids [#0004] [#0005].\n"
    assert "#0003 superseded -> #0004, #0005" in changes


def test_retarget_and_status(tmp_path):
    reg = _register(tmp_path)
    page = _page(tmp_path, "Text [#0001] [#0002/M/n=1].\n")
    lines = ["\t".join(["retarget", "#0001", "", "", "", "", "", "", "", "", "facts/x.md#z", "moved"]),
             "\t".join(["status", "#0002", "", "", "", "n=1; unsettled", "open", "", "", "", "", "unsettled"])]
    changes, _ = cd.apply(_delta(tmp_path, lines), [page], register=reg)
    rows = {r["id"]: r for r in cl.read_register(reg)}
    assert rows["#0001"]["owner"] == "facts/x.md#z"
    assert rows["#0002"]["status"] == "open" and rows["#0002"]["bound"] == "n=1; unsettled"
    assert open(page, encoding="utf-8").read() == "Text [#0001] [#0002/M/n=1/open].\n"
    assert changes == ["#0001 owner facts/x.md#a -> facts/x.md#z", "#0002 status -> open"]


def test_an_invalid_add_writes_nothing(tmp_path):
    reg = _register(tmp_path)
    before = open(reg, encoding="utf-8").read()
    page = _page(tmp_path, "Text [T7.1].\n")
    with pytest.raises(cd.DeltaError):
        cd.apply(_delta(tmp_path, [_add("T7.1", claim="")]), [page], register=reg)
    assert open(reg, encoding="utf-8").read() == before
    assert open(page, encoding="utf-8").read() == "Text [T7.1].\n"


def test_dry_run_writes_nothing_and_reports(tmp_path):
    reg = _register(tmp_path)
    before = open(reg, encoding="utf-8").read()
    page = _page(tmp_path, "Text [T7.1].\n")
    changes, pages = cd.apply(_delta(tmp_path, [_add("T7.1")]), [page], register=reg, dry_run=True)
    assert changes == ["T7.1 -> #0004"] and pages == [page]
    assert open(reg, encoding="utf-8").read() == before


def test_unknown_op_and_bad_header_fail(tmp_path):
    p = tmp_path / "d.tsv"
    p.write_text("op\tid\n", encoding="utf-8")
    with pytest.raises(cd.DeltaError):
        cd.read_delta(str(p))
    p.write_text(HEADER + "\n" + "\t".join(["drop", "#0001"] + [""] * 10) + "\n", encoding="utf-8")
    with pytest.raises(cd.DeltaError):
        cd.read_delta(str(p))


def test_leftover_provisional_tags_are_reported(tmp_path, capsys):
    reg = _register(tmp_path)
    page = _page(tmp_path, "Text [T7.1] and [T7.9].\n")
    rc = cd.main(["apply", _delta(tmp_path, [_add("T7.1")]), "--pages", page, "--register", reg])
    out = capsys.readouterr().out
    assert rc == 0 and "T7.1 -> #0004" in out and "WARNING: provisional tags left" in out and "T7.9" in out
```

Add to `tools/tests/test_claims_check.py`:

```python
def test_view_accepts_a_page_path(tmp_path, capsys):
    reg = tmp_path / "claims.tsv"
    rows = [dict(zip(cl.COLUMNS, ["#0001", "A.", "C", "jar:A.b @1 L2", "", "settled", "", "mechanism", "s", "facts/x.md#a"])),
            dict(zip(cl.COLUMNS, ["#0002", "B.", "C", "jar:A.c @1 L2", "", "settled", "", "mechanism", "s", "facts/xy.md#a"])),
            dict(zip(cl.COLUMNS, ["#0003", "C.", "C", "jar:A.d @1 L2", "", "settled", "", "mechanism", "s", "platform/x.md#a"]))]
    cl.write_register(str(reg), rows)
    cc.main(["--register", str(reg), "--view", "facts/x.md"])
    out = capsys.readouterr().out
    assert "#0001" in out and "#0002" not in out and "#0003" not in out
    cc.main(["--register", str(reg), "--view", "facts"])
    out = capsys.readouterr().out
    assert "#0001" in out and "#0002" in out and "#0003" not in out
```

(`cc` is the module import the file already uses for `claims_check`; `cl` for `claimslib` — match the file's existing import names.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /c/Users/Angus/repos/project_zomboid && python -m pytest tools/tests/test_claims_delta.py tools/tests/test_claims_check.py -q -k "delta or view_accepts"`
Expected: FAIL — `ModuleNotFoundError: claims_delta`; the view test fails on `#0002` present.

- [ ] **Step 3: Write `tools/claims_delta.py`**

```python
#!/usr/bin/env python3
"""Apply a page task's claims delta to the register (spec § The claims register, "Deltas in Phases 2 and 3").

A delta file is tab-separated with the header
  op  id  claim  grade  pointer  bound  status  successor  kind  source  owner  reason
and one delta per line. `add` names a provisional id `T<task>.<n>`: apply mints the next free register
id for it and rewrites that provisional tag in every page named with --pages. `split` names a real
parent id and is followed by exactly two `add` lines, which become the parent's successors; the parent
goes superseded and its tag on the pages is rewritten to the two children. `retarget` changes the
row's owner. `status` changes the row's status (and its successor when superseded; its bound when
the delta gives one). Nothing is ever deleted; an invalid delta aborts before anything is written.

Usage: python tools/claims_delta.py apply <delta.tsv> --pages <page.md> [...] [--register TSV] [--dry-run]"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claimslib as cl

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO_ROOT, "docs", "reference", "claims.tsv")
DELTA_COLUMNS = ("op",) + cl.COLUMNS + ("reason",)
OPS = ("add", "retarget", "status", "split")


class DeltaError(Exception):
    pass


def read_delta(path):
    with open(path, encoding="utf-8", newline="") as f:
        lines = [l.rstrip("\r") for l in f.read().split("\n")]
    if not lines or lines[0].split("\t") != list(DELTA_COLUMNS):
        raise DeltaError("%s: header must be %s" % (path, "\t".join(DELTA_COLUMNS)))
    out = []
    for n, line in enumerate(lines[1:], 2):
        if not line.strip():
            continue
        cells = line.split("\t")
        if len(cells) != len(DELTA_COLUMNS):
            raise DeltaError("%s:%d: %d cells, expected %d" % (path, n, len(cells), len(DELTA_COLUMNS)))
        d = dict(zip(DELTA_COLUMNS, cells))
        if d["op"] not in OPS:
            raise DeltaError("%s:%d: unknown op %r" % (path, n, d["op"]))
        out.append(d)
    return out


def _next_id(rows):
    return cl.id_str(max((cl.id_int(r["id"]) for r in rows), default=0) + 1)


def _mint(d, new_rows, tag_map, note=""):
    if not cl.is_provisional(d["id"]):
        raise DeltaError("add %s: id must be provisional (T<task>.<n>)" % d["id"])
    if d["id"] in tag_map:
        raise DeltaError("add %s: provisional id used twice" % d["id"])
    row = {c: d[c] for c in cl.COLUMNS}
    row["id"] = _next_id(new_rows)
    errs = cl.validate_row(row)
    if errs:
        raise DeltaError("add %s: %s" % (d["id"], "; ".join(errs)))
    new_rows.append(row)
    tag_map[d["id"]] = row["id"]
    return row, "%s -> %s%s" % (d["id"], row["id"], note)


def plan(rows, deltas):
    """(new_rows, tag_map, changes) with nothing written; raises DeltaError on the first bad delta."""
    new_rows = [dict(r) for r in rows]
    by = {r["id"]: r for r in new_rows}
    tag_map, changes, i = {}, [], 0
    while i < len(deltas):
        d = deltas[i]
        if d["op"] == "add":
            row, msg = _mint(d, new_rows, tag_map)
            by[row["id"]] = row
            changes.append(msg)
            i += 1
        elif d["op"] == "split":
            parent = by.get(d["id"])
            if parent is None:
                raise DeltaError("split %s: no such row" % d["id"])
            kids = deltas[i + 1:i + 3]
            if len(kids) != 2 or any(k["op"] != "add" for k in kids):
                raise DeltaError("split %s: must be followed by exactly two add lines" % d["id"])
            ids = []
            for k in kids:
                row, msg = _mint(k, new_rows, tag_map, " (split of %s)" % d["id"])
                by[row["id"]] = row
                ids.append(row["id"])
                changes.append(msg)
            parent["status"], parent["successor"] = "superseded", ", ".join(ids)
            tag_map[d["id"]] = parent["successor"]
            changes.append("%s superseded -> %s" % (d["id"], parent["successor"]))
            i += 3
        elif d["op"] == "retarget":
            row = by.get(d["id"])
            if row is None:
                raise DeltaError("retarget %s: no such row" % d["id"])
            if not cl.OWNER_RX.match(d["owner"]):
                raise DeltaError("retarget %s: owner %r is not <layer>/<page>.md#<anchor>" % (d["id"], d["owner"]))
            changes.append("%s owner %s -> %s" % (d["id"], row["owner"], d["owner"]))
            row["owner"] = d["owner"]
            i += 1
        else:
            row = by.get(d["id"])
            if row is None:
                raise DeltaError("status %s: no such row" % d["id"])
            if d["status"] not in cl.STATUSES:
                raise DeltaError("status %s: %r not in %s" % (d["id"], d["status"], cl.STATUSES))
            row["status"] = d["status"]
            row["successor"] = d["successor"] if d["status"] == "superseded" else ""
            if d["bound"]:
                row["bound"] = d["bound"]
            errs = cl.validate_row(row)
            if errs:
                raise DeltaError("status %s: %s" % (d["id"], "; ".join(errs)))
            changes.append("%s status -> %s" % (d["id"], d["status"]))
            i += 1
    return new_rows, tag_map, changes


def rewrite_page(text, tag_map, by_id):
    """Rewrites every tag bracket naming a mapped id (a provisional id, or a split parent) and re-canonicalises it."""
    def fix(m):
        bracket = m.group(0)
        if not (cl.TAG_RX.match(bracket) or cl.find_provisional(bracket)):
            return bracket                     # a markdown link or plain brackets
        items = []
        for cid, suffix in cl.split_tag(m.group(1)):
            for t in [x.strip() for x in tag_map.get(cid, cid).split(",")]:
                items.append(t + (cl.canonical_suffix(by_id[t]) if t in by_id else suffix))
        return "[" + ", ".join(dict.fromkeys(items)) + "]"
    return cl.BRACKET_RX.sub(fix, text)


def apply(delta_path, pages, register=REGISTER, dry_run=False):
    rows = cl.read_register(register)
    new_rows, tag_map, changes = plan(rows, read_delta(delta_path))
    by_id = {r["id"]: r for r in new_rows}
    rewritten = {}
    for p in pages:
        with open(p, encoding="utf-8", newline="") as f:
            text = f.read()
        new = rewrite_page(text, tag_map, by_id)
        if new != text:
            rewritten[p] = new
    if not dry_run:
        cl.write_register(register, new_rows)
        for p, text in rewritten.items():
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(text)
    return changes, sorted(rewritten)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("apply")
    a.add_argument("delta"); a.add_argument("--pages", nargs="+", required=True)
    a.add_argument("--register", default=REGISTER); a.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    try:
        changes, pages = apply(args.delta, args.pages, register=args.register, dry_run=args.dry_run)
    except (DeltaError, cl.RegisterError, OSError) as e:
        print("error: %s" % e)
        return 1
    for c in changes:
        print(c)
    print("pages rewritten: %s" % (", ".join(pages) if pages else "none") + (" (dry run)" if args.dry_run else ""))
    for p in args.pages:
        with open(p, encoding="utf-8", newline="") as f:
            left = sorted(set(cl.find_provisional(f.read())))
        if left:
            print("WARNING: provisional tags left on %s: %s" % (p, ", ".join(left)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Then in `tools/claims_check.py` `main`, replace the `--view` loop with:

```python
        if a.view:
            v = a.view.rstrip("/")
            prefix = v + "#" if v.endswith(".md") else v + "/"
            for r in rows:
                if r["owner"].startswith(prefix):
                    print("\t".join(r[c] for c in cl.COLUMNS))
```

and in the module docstring change `--view LAYER` to `--view LAYER|LAYER/PAGE.md`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /c/Users/Angus/repos/project_zomboid && python -m pytest tools/tests -q`
Expected: all pass (349 + 9).

- [ ] **Step 5: README entry and a live dry run**

Add under `tools/README.md` § Reference tooling, after the `claims_check.py` entry:

```markdown
- `claims_delta.py` — `python tools/claims_delta.py apply <delta.tsv> --pages <page.md>… [--register TSV] [--dry-run]`.
  The controller's tool for a page task's delta file (spec § The claims register, "Deltas in Phases 2 and 3";
  the file shape is `docs/superpowers/plans/restructure-2-page-procedure.md` § 6): mints the next free id for
  each `add`, supersedes a `split` parent with its two children, retargets an owner, changes a status; rewrites
  the provisional tags on the named pages and re-canonicalises them; prints every change and any provisional
  tag it did not cover; exits 1 and writes nothing on an invalid delta. Never deletes a row.
```

and extend the `claims_check.py` entry's `--view` clause to "`--view LAYER` prints a layer's rows, `--view LAYER/PAGE.md` one page's". Then prove the tool against the real register without writing:

Run: `cd /c/Users/Angus/repos/project_zomboid && printf 'op\tid\tclaim\tgrade\tpointer\tbound\tstatus\tsuccessor\tkind\tsource\towner\treason\nadd\tT1.1\tSmoke.\tC\tjar:A.b @1 L2\t\tsettled\t\tmechanism\tdocs/vanilla/x.md § Y\tfacts/x.md#a\tsmoke\n' > "$TEMP/d.tsv" && printf 'x [T1.1]\n' > "$TEMP/p.md" && python tools/claims_delta.py apply "$TEMP/d.tsv" --pages "$TEMP/p.md" --dry-run && python tools/claims_check.py --view facts/spoilage.md | wc -l`
Expected: `T1.1 -> #2040`, `pages rewritten: … (dry run)`, then `63`; `git status --short` shows only the four intended files.

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git add tools/claims_delta.py tools/tests/test_claims_delta.py && git commit -m "claims_delta: apply a page task's delta; claims_check --view <page>" -- tools/claims_delta.py tools/tests/test_claims_delta.py tools/claims_check.py tools/tests/test_claims_check.py tools/README.md
```

---

### Task 2: `tools/page_lint.py` — the page contract as rules

**Files:**
- Create: `tools/page_lint.py`, `tools/tests/test_page_lint.py`
- Modify: `tools/README.md` § Reference tooling (one entry)

**Interfaces:**
- Consumes: `claimslib.read_register`, `iter_tags`, `TAG_RX`; the register (`--register` override for tests).
- Produces: `python tools/page_lint.py <page.md> [...] [--partial] [--register TSV] [--cap N]` — one finding per line `path:line: rule: detail`, a `prose <n> lines (cap <cap>)` line per page, `N findings, M warnings`; exit 1 on a finding. Rules: `stamp`, `section` (missing, unknown or out of order), `anchor` (an owned row's anchor missing; a duplicate `<a id>`), `rule-line` (a `## Rules` line without `: ` or without a closing tag; a `## Key facts` line without a closing tag), `walls` (no closing `Not covered:` line), `narrative`, `prose` (over the cap; `prose-floor` warning under 150), `example` (a `## Worked examples` path missing), `link` (a relative link to a missing page or anchor; a missing page is skipped under `--partial`).

- [ ] **Step 1: Write the failing tests**

`tools/tests/test_page_lint.py`:

```python
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

<a id="walls"></a>
## Walls and bounds
- One bound [#0002/M/n=1].
Not covered: the freezer.

<a id="open"></a>
## Open
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
    no_open = GOOD.replace("<a id=\"open\"></a>\n## Open\n- A question -> X7 [#0002/M/n=1].\n\n", "")
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /c/Users/Angus/repos/project_zomboid && python -m pytest tools/tests/test_page_lint.py -q`
Expected: FAIL — `ModuleNotFoundError: page_lint`.

- [ ] **Step 3: Write `tools/page_lint.py`**

```python
#!/usr/bin/env python3
"""The page lint: the page contract (spec § The page contract) for docs/areas, docs/platform, docs/facts.

Per page: the stamp line; the section set and order for its layer; the <a id> anchors (every register
row owned by the page has its anchor on the page; no duplicate); a `## Rules` line has a colon and ends
with a tag, a `## Key facts` line ends with a tag; `## Walls and bounds` ends with a "Not covered:"
line; no narrative marker outside code spans; the prose line count against the cap (over the cap
fails; under 150 warns; tables, fences, headings, anchor lines and `## Open` index rows do not count);
every `## Worked examples` path exists; every relative link resolves to a page and, when it names one,
an anchor (--partial skips a missing page). Exit 1 on a finding; a warning never fails.

Usage: python tools/page_lint.py <page.md> [...] [--partial] [--register TSV] [--cap N] [--root DIR]"""
import argparse, collections, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claimslib as cl

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = "docs/reference/claims.tsv"
STAMP_RX = re.compile(r"^Verified against 42\.20\.4 \(b0bbce05d5\) · \d{4}-\d{2}-\d{2} · scope: \S.*$")
NARRATIVE_RX = re.compile(r"\b(previously|corrected 20|resolved (in|by) slice|RESOLVED 20|CONTESTED|the review found|this slice)\b")
CODE_SPAN_RX = re.compile(r"`[^`]*`")
ANCHOR_RX = re.compile(r'^<a id="([a-z0-9-]+)"></a>\s*$')
LINK_RX = re.compile(r"\]\(([^)\s#]*)(#[a-z0-9-]+)?\)")
FILE_LINES_RX = re.compile(r"([A-Za-z0-9_./-]+\.[A-Za-z0-9]+):\d+(?:[-–]\d+)?")
# A trailing `?` marks an optional section; the order is the contract's.
SECTIONS = {
    "platform": ["Rules", "How it works", "Walls and bounds", "Open", "Worked examples?", "Procedure?", "See also"],
    "facts": ["Key facts", "How it works", "Walls and bounds", "Open", "Worked examples?", "See also"],
    "areas": ["Rules", "How it works", "Options", "Walls and bounds", "Open", "Worked examples?", "See also"],
}
PAGE_SECTIONS = {"platform/overview.md": ["Rules", "How it works", "Coverage", "Open", "Worked examples?", "See also"]}
CAPS = {"platform/harness.md": 500, "platform/mod-anatomy.md": 500, "platform/lua-platform.md": 500, "platform/mp-model.md": 500}
DEFAULT_CAP, FLOOR = 400, 150
WARN_RULES = ("prose-floor",)
Finding = collections.namedtuple("Finding", "path line rule detail")


def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read().replace("\r\n", "\n")


def _sections(lines):
    """[(heading or '', [(n, line), ...])] split on `## ` headings; the preamble has heading ''."""
    out, cur = [], ("", [])
    for n, line in enumerate(lines, 1):
        if line.startswith("## "):
            out.append(cur); cur = (line[3:].strip(), [])
        else:
            cur[1].append((n, line))
    out.append(cur)
    return out


def _page_key(path, root):
    rel = os.path.relpath(path, root).replace("\\", "/")
    return rel[len("docs/"):] if rel.startswith("docs/") else rel


def lint(path, root=REPO_ROOT, register=None, partial=False, cap=None):
    rel = os.path.relpath(path, root).replace("\\", "/")
    key = _page_key(path, root)
    layer = key.split("/")[0]
    text = _read(path)
    lines = text.split("\n")
    out = []
    # stamp
    if len(lines) < 2 or not STAMP_RX.match(lines[1]):
        out.append(Finding(rel, 2, "stamp", "line 2 must read 'Verified against 42.20.4 (b0bbce05d5) · <date> · scope: <one line>'"))
    # sections
    spec = PAGE_SECTIONS.get(key) or SECTIONS.get(layer, SECTIONS["facts"])
    names = [s.rstrip("?") for s in spec]
    required = [s for s in spec if not s.endswith("?")]
    secs = _sections(lines)
    present = [h for h, _ in secs if h]
    for h in present:
        if h not in names:
            out.append(Finding(rel, 1, "section", "unknown section '## %s' for %s" % (h, layer)))
    for r in required:
        if r not in present:
            out.append(Finding(rel, 1, "section", "missing section '## %s'" % r))
    order = [h for h in present if h in names]
    if order != sorted(order, key=names.index):
        out.append(Finding(rel, 1, "section", "sections out of order: %s" % " > ".join(order)))
    # anchors
    seen = {}
    for n, line in enumerate(lines, 1):
        m = ANCHOR_RX.match(line)
        if m:
            if m.group(1) in seen:
                out.append(Finding(rel, n, "anchor", "duplicate anchor #%s (first at line %d)" % (m.group(1), seen[m.group(1)])))
            seen.setdefault(m.group(1), n)
    reg_path = register or os.path.join(root, *REGISTER.split("/"))
    if os.path.exists(reg_path):
        for r in cl.read_register(reg_path):
            page, _, anchor = r["owner"].partition("#")
            if page == key and r["status"] != "superseded" and anchor and anchor not in seen:
                out.append(Finding(rel, 1, "anchor", "%s is owned by #%s but the page has no <a id=\"%s\">" % (r["id"], anchor, anchor)))
    # section bodies
    fence = False
    prose = 0
    for heading, body in secs:
        for n, line in body:
            if line.startswith("```"):
                fence = not fence; continue
            if fence:
                continue
            stripped = line.strip()
            if heading in ("Rules", "Key facts") and stripped.startswith("- "):
                if not re.search(r"\[#\d{4}[^\]]*\]\.?\s*$", stripped):
                    out.append(Finding(rel, n, "rule-line", "a %s line must end with its tag: %s" % (heading, stripped[:60])))
                elif heading == "Rules" and ": " not in stripped:
                    out.append(Finding(rel, n, "rule-line", "a rule line is '<imperative>: <reason> [#tag]': %s" % stripped[:60]))
            bare = CODE_SPAN_RX.sub("", line)
            if NARRATIVE_RX.search(bare):
                out.append(Finding(rel, n, "narrative", "narrative marker: %s" % stripped[:60]))
            if heading == "Worked examples" and stripped.startswith("|") and not re.match(r"^\|\s*:?-", stripped):
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                if len(cells) >= 2 and cells[0].lower() != "shape":
                    m = FILE_LINES_RX.search(cells[1])
                    if not m or not os.path.exists(os.path.join(root, *m.group(1).split("/"))):
                        out.append(Finding(rel, n, "example", "worked example path does not exist: %s" % cells[1]))
            for m in LINK_RX.finditer(line):
                target, anchor = m.group(1), m.group(2)
                if target.startswith(("http://", "https://")) or (not target and not anchor):
                    continue
                tpath = os.path.normpath(os.path.join(os.path.dirname(path), target)) if target else path
                if not os.path.exists(tpath):
                    if not partial:
                        out.append(Finding(rel, n, "link", "link target does not exist: %s" % target))
                    continue
                if anchor and tpath.endswith(".md") and ('<a id="%s">' % anchor[1:]) not in _read(tpath):
                    out.append(Finding(rel, n, "link", "link anchor not found: %s%s" % (target, anchor)))
            if (not stripped or stripped.startswith("#") or stripped.startswith("|") or ANCHOR_RX.match(stripped)
                    or heading == "Open" or (heading == "" and n <= 2)):
                continue
            prose += 1
        if heading == "Walls and bounds":
            tail = [l for _, l in body if l.strip()]
            if not tail or not tail[-1].startswith("Not covered:"):
                out.append(Finding(rel, body[-1][0] if body else 1, "walls", "'## Walls and bounds' must end with a 'Not covered:' line"))
    limit = cap or CAPS.get(key, DEFAULT_CAP)
    if prose > limit:
        out.append(Finding(rel, 1, "prose", "%d prose lines, cap %d" % (prose, limit)))
    elif prose < FLOOR:
        out.append(Finding(rel, 1, "prose-floor", "%d prose lines, under the 150 the contract expects" % prose))
    return out, prose


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pages", nargs="+"); ap.add_argument("--root", default=REPO_ROOT); ap.add_argument("--register")
    ap.add_argument("--partial", action="store_true"); ap.add_argument("--cap", type=int)
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    findings = []
    for p in a.pages:
        f, prose = lint(os.path.abspath(p), root=os.path.abspath(a.root), register=a.register, partial=a.partial, cap=a.cap)
        findings += f
        print("%s: prose %d lines (cap %d)" % (os.path.relpath(p, a.root).replace("\\", "/"), prose, a.cap or CAPS.get(_page_key(os.path.abspath(p), os.path.abspath(a.root)), DEFAULT_CAP)))
    for f in sorted(findings, key=lambda f: (f.path, f.line, f.rule)):
        print("%s:%d: %s: %s%s" % (f.path, f.line, f.rule, f.detail, " (warning)" if f.rule in WARN_RULES else ""))
    n_err = sum(1 for f in findings if f.rule not in WARN_RULES)
    print("%d findings, %d warnings" % (n_err, len(findings) - n_err))
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /c/Users/Angus/repos/project_zomboid && python -m pytest tools/tests -q`
Expected: all pass (358 + 8). If a test's expected prose count differs by one from the fixture, fix the fixture, not the counting rule (the rule is stated in the docstring).

- [ ] **Step 5: README entry**

Add under `tools/README.md` § Reference tooling, after the `claims_delta.py` entry:

```markdown
- `page_lint.py` — `python tools/page_lint.py <page.md>… [--partial] [--register TSV] [--cap N]`. The page
  contract (spec § The page contract) as rules for `docs/areas`, `docs/platform`, `docs/facts`: the stamp
  line, the section set and order per layer, the `<a id>` anchors against the register's owners, the
  rule-line shape, the closing `Not covered:` line, the narrative markers, the prose cap (400; 500 on the four
  pages the spec allows; under 150 warns), worked-example paths, relative links and their anchors
  (`--partial` skips a page not written yet). Prints the prose count per page; exit 1 on a finding.
```

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Angus/repos/project_zomboid && git add tools/page_lint.py tools/tests/test_page_lint.py && git commit -m "page_lint: the page contract as rules" -- tools/page_lint.py tools/tests/test_page_lint.py tools/README.md
```

---

## The page tasks

Every task below follows `docs/superpowers/plans/restructure-2-page-procedure.md` exactly (inputs, page shape, sentences, walls and open, deltas, validation, commit, report). Each task's text is only what is particular to its page. Row and anchor counts are from the register at `#2039` (non-superseded rows), so a writer knows the shape of the work; the view is the authority. "Sources" lists the old docs the page's rows came from, most rows first; read every one named. Each page task's files are: Create `docs/<layer>/<page>.md`; write `.superpowers/sdd/restructure-2-platform-facts/task-<N>-delta.tsv` (if needed) and `task-<N>-report.md`. Each page task's steps are the procedure's: (1) `python tools/claims_check.py --view <layer>/<page>.md` and read the anchor plan section; (2) read the sources; (3) write the page; (4) `python tools/claims_check.py --partial --allow-provisional`, `python tools/claims_check.py --fix-tags`, `python tools/page_lint.py docs/<layer>/<page>.md --partial` → 0 findings; (5) `git add docs/<layer>/<page>.md && git commit -m "Page: <layer>/<page>" -- docs/<layer>/<page>.md`; (6) the report.

### Task 3: `facts/eating-pipeline.md`

- Rows 122: mechanism 107, contradiction 6, open 7, order 1, bound 1. Anchors: `#getters` 6, `#eat` 7 (the `Eat` block is the one `order` row — the annotated bytecode transcript from `docs/vanilla/eating-pipeline.md` § The `Eat` algorithm, verbatim, tagged on its caption), `#modifiers` 38 (the modifier ladder as one table with a tag per row — the table's rows are the register's rows, not a dataset), `#partial` 9, `#fluid-path` 22, `#eat-type` 4, `#duration` 10, `#script-scale` 2, `#sandbox` 10 (the `Nutrition` sandbox option table), `#walls` 7 (six mirror contradictions), `#open` 7.
- Sources: `docs/vanilla/eating-pipeline.md` (115 rows), `docs/vanilla/food-dataset-notes.md` (17), `docs/vanilla/food-item-model.md` (4), `data/README.md` (2).
- Cap 400. The apple's 95 kcal worked example (`#script-scale`) is the one per-food value that appears on the page; every other per-food value stays in the dataset. `## Key facts` carries the pipeline's load-bearing numbers (the order of writes, the fraction rescale, the sandbox gate, the fluid per-litre chain).
- Hands off: the hook dispatch mechanics are `platform/lua-platform.md#script-hooks` (cite, never restate); the packets `Eat` sends are `facts/wire-packets.md`.

### Task 4: `facts/food-item-model.md`

- Rows 49: mechanism 41, count 3, contradiction 1, open 2, rule 1, table 1. Anchors: `#state-axes` 9, `#dead-setters` 7, `#script-keys` 5 (the 114-key table is one `table` row: carry the table verbatim from `docs/vanilla/food-item-model.md` under one tagged caption, the four rows singled out beside it), `#poison` 10, `#dataset-fidelity` 13 (the census, the spot checks by type, the absent-against-zero read-backs, the fluid join, the three-drink probe — measured rows, most `M`), `#walls` 3, `#open` 2 (one `unverified` row).
- Sources: `docs/vanilla/food-item-model.md` (26), `docs/vanilla/food-dataset-notes.md` (17), `docs/vanilla/eating-pipeline.md` (7), `docs/mods-survey/teardowns/longtermpreservation4220.md` (4), `docs/modding/item-overrides.md` (2).
- Cap 400. The loader's per-key merge and replay are `platform/loader-and-scripts.md` (cite); the dataset columns are `reference/datasets.md` (link, not written yet: `--partial`).

### Task 5: `facts/spoilage.md`

- Rows 63: mechanism 46, contradiction 4, count 3, open 7, order 1, rule 1, bound 1. Anchors: `#formula` 6 (the aging formula block is the `order` row), `#containers` 10, `#spawn-age` 2, `#sealed` 14, `#writes` 9, `#measured` 4 (one table: rate per arm with its run), `#sandbox` 6, `#walls` 5, `#open` 7.
- Sources: `docs/vanilla/food-item-model.md` (62), `docs/vanilla/recipes-dataset-notes.md` (5), `docs/vanilla/food-dataset-notes.md` (3), `docs/mods-survey/teardowns/longtermpreservation4220.md` (2).
- Cap 400. The `ReplaceOn*` links a dataset cannot resolve are stated under `#sealed` as a fact about the dataset, citing its row.

### Task 6: `facts/cooking-and-recipes.md`

- Rows 121: mechanism 83, count 13, open 7, rule 6, bound 6, contradiction 3, order 2, table 1. Anchors: `#cook-block` 22 (the cook block is an `order` row: the five-branch burn block verbatim), `#uses` 19, `#evolved` 30, `#evolved-join` 14, `#type-change` 15 (one table of deltas), `#dataset-fidelity` 5, `#walls` 9, `#open` 7.
- Sources: `docs/vanilla/recipes-dataset-notes.md` (66), `docs/vanilla/food-item-model.md` (56), `docs/mods-survey/teardowns/longtermpreservation4220.md` (2), `docs/mods-survey/teardowns/autocook.md` (1), `docs/testing/README.md` (1), `data/README.md` (1).
- Cap 400. The `craftRecipe` grammar (general to any mod) is `platform/loader-and-scripts.md#craft-recipe-grammar` — cite; the 31 craft deltas and the 26-row tables stay one tag each.

### Task 7: `facts/body-and-weight.md`

- Rows 141: mechanism 114, contradiction 17, open 6, count 2, order 1, table 1. Anchors: `#time-unit` 1, `#passive-burn` 18, `#hunger-thirst` 13, `#multipliers` 8, `#fill-times` 10 (one derived table), `#coupling` 5, `#moodles` 26 (the 30-row band table is the `table` row; the thresholds and drivers as one tagged table), `#weight-bands` 8, `#weight-traits` 16, `#traits` 7, `#sandbox` 6, `#walls` 17 (seventeen mirror contradictions: one line each, `The mirror says …; the code does …`), `#open` 6.
- Sources: `docs/vanilla/body-stats.md` (133), `docs/vanilla/nutrition-core.md` (14), `docs/modding/patterns.md` (4), `docs/modding/wall-map.md` (4).
- Cap 400 — the densest facts page: tables for the rates, the fill times, the moodle thresholds and the weight bands keep the prose inside the cap. The weight model itself is `facts/nutrition-core.md#weight-model` (cite).

### Task 8: `facts/nutrition-core.md`

- Rows 34: mechanism 30, bound 2, open 1, order 1. Anchors: `#weight-model` 11 (the `order` row is the annotated `updateWeight` block), `#clamps` 6, `#verified` 12 (the three-day server verification: predicted, measured, the difference — a table), `#macro-effects` 2, `#walls` 2, `#open` 1.
- Sources: `docs/vanilla/nutrition-core.md` (26), `docs/modding/wall-map.md` (5), `docs/vanilla/eating-pipeline.md` (3), `docs/modding/lua-api.md` (2), `docs/modding/patterns.md` (2).
- Cap 400; expect the shortest facts page (about 150–200 prose lines). Ownership of the weight quantity is `platform/mp-model.md#ownership` (cite).

### Task 9: `facts/wire-packets.md`

- Rows 79: mechanism 66, table 5, open 4, count 2, order 1, rule 1. Anchors: `#item-stats-packet` 27 (the field contract as one tagged table plus the omissions), `#player-stats-packet` 10, `#moddata-packet` 2, `#eat-food-packet` 2, `#cooked-thirst` 4, `#desyncs` 24 (one table: field, arm, reading, run — each row tagged), `#staircase` 4, `#walls` 2, `#open` 4.
- Sources: `docs/vanilla/food-item-model.md` (21), `docs/mods-survey/teardowns/longtermpreservation4220.md` (18), `docs/vanilla/eating-pipeline.md` (9), `docs/mods-survey/teardowns/simplestatus.md` (9), `docs/modding/patterns.md` (8), `docs/modding/lua-api.md` (7), `docs/modding/item-overrides.md` (7), `docs/modding/wall-map.md` (6).
- Cap 400. The packet mechanisms (what a packet is, when it fires, wipe-and-replace, the cached packet) are `platform/mp-model.md` — this page owns the field contracts and the measured desyncs only (spec "Sync placement").

### Task 10: `facts/other-mods/autocook.md`

- Rows 47: mechanism 36, rule 6, table 3, order 1, bound 1. Anchors: `#what-it-does` 2, `#architecture` 9, `#data-model` 7, `#techniques` 6 (`## Key facts`), `#pitfalls` 7, `#compat` 9, `#mp` 6, `#open` 1. Section mapping per procedure § 3.
- Source: `docs/mods-survey/teardowns/autocook.md` (48 rows; 800 lines — read it whole).
- Cap 400; expect 150–250 prose lines. Engine facts the teardown discovered are owned by `platform/` or `facts/` rows (cite them from `#pitfalls`, never restate).

### Task 11: `facts/other-mods/longtermpreservation.md`

- Rows 29: mechanism 21, rule 5, table 2, count 1. Anchors: `#what-it-does` 3, `#architecture` 10, `#techniques` 5, `#pitfalls` 6, `#compat` 4, `#mp` 1; `#open` has no rows — write the one-line "what the teardown did not settle" from the teardown's own open list, tag-free only if it states no number, else a delta.
- Source: `docs/mods-survey/teardowns/longtermpreservation4220.md` (713 lines).
- Cap 400; the page's title is the mod's name; the workshop id and the tree-qualified paths appear as facts with their tags.

### Task 12: `facts/other-mods/simplestatus.md`

- Rows 31: mechanism 22, rule 6, table 3. Anchors: `#what-it-does` 4, `#architecture` 10, `#techniques` 5, `#pitfalls` 6, `#compat` 4, `#mp` 2; `#open` has no rows (as Task 11).
- Source: `docs/mods-survey/teardowns/simplestatus.md` (815 lines). The mod's `mods/SimpleStatus/` on-disk path form is the register's (R23); quote pointers never, paths as facts only where a row states them.
- Cap 400.

### Task 13: `facts/other-mods/beyondten.md`

- Rows 9: mechanism 6, rule 3. Anchors: `#what-it-does` 1, `#architecture` 3, `#techniques` 3, `#pitfalls` 1, `#mp` 1; `#compat` and `#open` have no rows — one line each from the teardown, no numbers.
- Source: `docs/mods-survey/teardowns/beyondten.md` (91 lines).
- Cap 400; the page will sit under the 150-line floor (a warning, accepted — say so in the report). A short page that states its nine rows honestly beats padding.

### Task 14: `facts/other-mods/itemquality.md`

- Rows 10: mechanism 7, rule 3. Anchors: `#what-it-does` 1, `#architecture` 3, `#techniques` 1, `#pitfalls` 3, `#mp` 2; `#compat` and `#open` as Task 13.
- Source: `docs/mods-survey/teardowns/itemquality.md` (106 lines). Under the floor, accepted.

### Task 15: `facts/other-mods/catalog.md`

- Rows 92: count 36, mechanism 34, table 9, verdict 7, bound 3, open 2, rule 1. Anchors: `#sweep` 29 (the dated sweeps: every count carries its date and its `web:`/`data:` row), `#status` 20 (the B42 status table as tagged rows), `#api-surface` 12 (one table), `#corpus-facts` 25, `#walls` 4 (each with its snapshot date), `#open` 2.
- Sources: `docs/mods-survey/nutrition-mods.md` (86), `docs/mods-survey/approved-modlist.md` (20), `docs/mods-survey/README.md` (6), `docs/modding/wall-map.md` (4).
- Cap 400. The seven `verdict` rows are wall-map rows the survey grounds: cite by id from `#walls` or `#corpus-facts`. The mod inventory columns are `reference/datasets.md#mod-inventory` (link).

### Task 16: `platform/mod-anatomy.md`

- Rows 86: mechanism 69, open 6, bound 3, rule 3, contradiction 2, count 1, order 1, table 1. Anchors: `#mod-info-keys` 7, `#load-order-declarations` 5, `#mod-discovery` 6, `#id-chain` 10, `#version-dirs` 13, `#folder-name` 3, `#translations` 20, `#missing-mod` 3, `#build-pinning` 1, `#join` 2, `#checksum-gate` 2 (all three arms, the normalisation, the bypass role, the AntiCheat timeout — the spec's hard case), `#client-only-mods` 3, `#walls` 5, `#open` 6.
- Sources: `docs/modding/anatomy.md` (52), `docs/mods-survey/teardowns/autocook.md` (11), `docs/modding/item-overrides.md` (8), `docs/modding/wall-map.md` (6), `docs/mods-survey/nutrition-mods.md` (5), `docs/modding/patterns.md` (4).
- Cap 500. `## Rules` 10–20 lines (the anatomy KEEP rules: one id per folder, ship `common/` beside a version dir, pin the build, byte-identical files on both sides …). `## Worked examples` required: candidates `testing/experiments/tkx-loader-probe/common/mod.info` and `42.20/mod.info` (two mod.infos), `testing/experiments/TKX_CommonOnly/` (a `common/`-only tree), `testing/profiles/missing-mod.toml` (the missing-mod arm), `testing/experiments/x123_folder.py` (the folder-name and id-chain reads), `testing/experiments/x122_loader.py`. Each row: shape, `file:lines` (re-located), what it shows.
- The file-level merge (version dir over `common/`, `LoadDirBase`'s vanilla-first dedupe, translations) is this page's; the block-level script merge is `loader-and-scripts.md` (spec "Two merges").

### Task 17: `platform/loader-and-scripts.md`

- Rows 69: mechanism 65, bound 2, count 1, open 1. Anchors (16): `#file-map` 11, `#lua-load-order` 6, `#script-dsl` 7, `#craft-recipe-grammar` 3, `#file-list` 2, `#bucket-append` 3, `#per-key-merge` 10, `#sorted-replay` 8, `#path-collisions` 2, `#default-moddata` 4, `#identity` 1, `#name-resolution` 2, `#per-side-load` 6, `#reload` 1, `#walls` 2 (plus X15, X19, X20, X27 as walls citing their open rows on `areas/open-questions.md` — link, `--partial`), `#open` 1.
- Sources: `docs/modding/item-overrides.md` (31), `docs/modding/anatomy.md` (12), `docs/modding/wall-map.md` (10), `docs/mods-survey/teardowns/longtermpreservation4220.md` (7), `docs/modding/patterns.md` (6), `docs/vanilla/recipes-dataset-notes.md` (5).
- Cap 400 (the anchor plan's split clause: if the page cannot fit, move `#file-map`, `#lua-load-order`, `#path-collisions`, `#per-side-load` to `platform/file-map.md` and file `retarget` deltas — report it as a concern first; the controller rules). `## Worked examples` required: `testing/experiments/TKX_ItemOverride/42.20/` (the minimal override block; find its script under `media/scripts/`), `testing/experiments/TKX_ZWatermelon/42.20/mod.info` (the sort-key probe), `testing/experiments/x121_overrides.py`, `x124_order.py`, `x125_order2.py`, `x122_loader.py`.

### Task 18: `platform/lua-platform.md`

- Rows 88: mechanism 80, open 3, order 2, rule 2, table 1. Anchors: `#kahlua-limits` 8, `#pcall` 7, `#raises` 7, `#debug-break` 4, `#java-members` 11, `#script-hooks` 20 (the hook dispatch mechanics — the spec's hard case: how `OnEat`, `OnCooked`, `OnCreate` resolve, which side calls each, `EatOnClient` applies no numbers, a `server/` wrapper of `ISEatFoodAction.complete` runs before `Eat`), `#events` 6, `#hooks` 2, `#registries` 7 (`MoodleType`, `CharacterTrait`, the two moodle walls), `#removed-apis` 4, `#file-io` 2, `#dev-loop` 7, `#open` 3; `#walls` has no rows — write it from the walls the anchors imply (the pinned moodle level, the unexposed `MoodleStat`, the file-scope raise being unmeasured — each citing the mechanism row) and close with `Not covered:`.
- Sources: `docs/modding/lua-api.md` (48), `docs/modding/wall-map.md` (11), `docs/vanilla/eating-pipeline.md` (8), `docs/testing/spikes.md` (8), `docs/vanilla/body-stats.md` (7), `docs/modding/item-overrides.md` (5).
- Cap 500. `## Worked examples` required: `testing/experiments/TKX_PcallProbe/42.20/media/lua/shared/TKX_PcallProbe.lua` (the caught nil call), `TKX_RaiseProbe/…/TKX_RaiseProbe.lua` (the gated raise), `TKX_EatHook/42.20/media/lua/server/TKX_EatHook_Server.lua` and `shared/TKX_EatHook.lua` (the hook seats), `testing/experiments/x126_pcall.py`, `x127_raise.py`.

### Task 19: `platform/mp-model.md`

- Rows 106: mechanism 91, rule 8, open 6, bound 1. Anchors: `#ownership` 31 (one line per quantity: which side owns it, what the other holds), `#shapes` 1, `#routes-client-to-server` 5, `#routes-server-to-client` 9, `#packets` 4 (mechanisms only; the field lists are `facts/wire-packets.md`), `#cached-packet` 5, `#item-moddata` 7, `#player-moddata` 6, `#wipe-and-replace` 9, `#command-bus` 1, `#what-a-client-copy-is` 18, `#walls` 1 (plus the wall-map rows E1–E12 cited by register id), `#open` 9 (six open rows, eleven unverified rows across the page listed here with their re-measurement).
- Sources: `docs/vanilla/eating-pipeline.md` (22), `docs/modding/patterns.md` (18), `docs/vanilla/body-stats.md` (17), `docs/vanilla/food-item-model.md` (16), `docs/modding/wall-map.md` (13), `docs/modding/lua-api.md` (11), `docs/mods-survey/teardowns/longtermpreservation4220.md` (8), `docs/vanilla/nutrition-core.md` (7), `docs/mods-survey/teardowns/autocook.md` (7), `docs/mods-survey/teardowns/simplestatus.md` (6).
- Cap 500. `## Rules` carries the measured MP sync rules (from `docs/modding/patterns.md` § Measured MP sync facts' KEEP rows, each with its reason and tag). `## Worked examples` required: `testing/experiments/TKX_Nutrient/42.20/media/lua/{server,client,shared}/` (a server-owned value pushed with `transmitModData`), `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua` (the bus dispatch), `testing/experiments/s08_witness.py` (client-first paired reads).

### Task 20: `platform/harness.md`

- Rows 199: mechanism 94, rule 44, bound 40, table 13, count 2, open 2, tool 2, order 1, verdict 1. Anchors: `#pzt` 4, `#profiles` 32 (the fourteen-row TOML schema is one `table` row), `#sandbox` 7, `#driven-client` 12, `#bus` 8, `#reading-a-reply` 17, `#probes` 25, `#witness` 12, `#scenarios` 11, `#cadence` 10, `#time` 10, `#artifacts-discipline` 13, `#driver-rules` 10, `#experiment-contract` 2 (the standing rules; the specs are `reference/experiments.md`), `#walls` 22, `#procedure` 2, `#open` 2 (plus the page's twelve `unverified` rows).
- Sources: `docs/testing/README.md` (81; CRLF, read only), `docs/testing/profiles.md` (42), `docs/testing/spikes.md` (18), `docs/modding/wall-map.md` (12), `docs/mods-survey/teardowns/simplestatus.md` (6), `docs/testing/pipeline-design.md` (6), `docs/reference/experiments.md` (2).
- Cap 500 with the split clause: the spec allows `harness.md` to split "into the instrument and the scenario layer". Write the page whole first; if the prose exceeds 500, move `#scenarios`, `#cadence`, `#time`, `#driver-rules`, `#experiment-contract` to `platform/harness-scenarios.md` (same contract, its own `#walls`/`#open`), file `retarget` deltas for those rows, and report it as a concern — the controller adds the section to the anchor plan. `## Rules` = the 44 `rule` rows distilled to the twenty the contract allows, the rest as tagged lines under their anchors. `## Procedure` (no tags needed on its numbers): profile → scenario → driver → evidence, from `docs/testing/README.md`. `## Worked examples` required: `testing/experiments/_template.py` (the house driver shape; its provenance keys), `td3_autocook.py` and `x121_overrides.py` (the shape's origins), `testing/profiles/mod-under-test.toml`, `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua` (`TK.register`, the index-first guard), a scenario file under `testing/PZTestKit/PZTestKit/42/media/lua/server/scenarios/`. The reply-reading rules (`#reading-a-reply`) live here, not in the generated `reference/harness-commands.md` (link to it for the command table).

### Task 21: `platform/lessons.md`

- Rows 39: rule 35, count 2, mechanism 1, bound 1. Anchors: `#rules` 20 (the KEEP rules — this is the page's `## Rules`, at the contract's twenty-line cap: one imperative, a colon, the mechanism reason, the tag of the mechanism row each rests on), `#anti-patterns` 11 (the FILTER rules, under `## How it works` as tagged lines: what the corpus does that this mod will not, each citing the row), `#testing-discipline` 2, `#corpus-drift` 6, `#measure-the-mechanism` 0 (write the reading from the rules that rest on it — the staircase, the mirror — citing their rows), `#walls` 0 (rules that hold only inside their bound: name the bound, cite the row), `#open` 0 (the lessons a later run would confirm or overturn: the four `unverified` rule rows listed with their re-measurement).
- Sources: `docs/modding/patterns.md` (23; CRLF, read only), `docs/modding/anatomy.md` (5), `docs/modding/lua-api.md` (4), `docs/testing/profiles.md` (4), `CLAUDE.md` § 8 (2: the two platform gotchas — `-debug` parks on an unguarded raise; the corpus drifts, so every count is dated — become rules here; the repository gotchas stay in `CLAUDE.md`).
- Cap 400; `## Worked examples` optional.

### Task 22: `platform/jar-research.md`

- Rows 5: tool 5, all at `#method`. Anchors with no rows: `#reading-the-jar` (the subcommands `grep|methods|refs|dump` and what each does and does not tell you — from `docs/reference/jar-method-notes.md` § Tool note, citing the five tool rows where a sentence states what a subcommand does), `#exposed` (the exposer dump as the exposure test — link `docs/reference/jar-method-notes.md`'s exposer table; state no count without a tag), `#walls` (what a jar read cannot settle: behaviour, timing, which side — each as a bound in words; cite `platform/lua-platform.md#java-members` for the exposure test), `#procedure` (`## Procedure`: the numbered steps for answering a question from the jar, from `C:\Users\Angus\pz-b42\WORKSPACE.md` (read-only; the disassembler lives there and is not part of this repository — say so) and `jar-method-notes.md`; numbers under `## Procedure` carry no tag), `#open` (the jar questions this library left unread — from `docs/reference/jar-method-notes.md` § Summary).
- Source: `docs/reference/jar-method-notes.md` (6 rows; the whole file).
- Cap 400; expect about 150 prose lines; `## Rules` (10–20): re-locate an offset by content before quoting it, write `Class.method @off L<n>`, treat `refs` as not a reverse-caller query, escape `$` for inner classes … each with its reason and the tool row's tag. `## Worked examples` optional (a `tool:` pointer's shape may be shown).

### Task 23: `platform/overview.md` — written last

- Rows 17: mechanism 8, table 4, bound 3, rule 2. Anchors: `#surfaces` 1, `#two-lua-states` 4, `#process-model` 9, `#coverage` 3; no rows: `#one-server` (one sentence per quantity, each linking `../platform/mp-model.md#ownership` and citing the ownership row's tag — no number), `#routing` (the table an agent reads first: one line per `platform/` and `facts/` page — its scope line and the mechanisms it owns, from the finished pages' anchors), `#open` (a topic with rows and no page, if any). No `## Walls and bounds`; `## Coverage` in its place (the page lint knows). `## Rules` 10–20 lines: the routing rules (read the owner page before restating a number; a topic marked absent is unknown, not a wall; every verdict is dedicated-server MP …), each citing a row.
- `## Coverage` is the spec § Coverage table verbatim in shape: general topics as `covered` (a page with rows), `touched` (rows, no page: sandbox options a mod declares, the UI framework, timed actions, the crafting pipeline, server admin and RCON, build detection, client-only mods, the events roster), `absent` (sounds, tiles and sprites, vehicles, world and map mods, Workshop publishing, the save format), and the never-written vanilla docs (`food-sources`, cooking XP, the cooking UI); it opens with the spec's paragraph ("`platform/` is not a modding manual …"). Each `touched` topic carries an `open` register row: where the register has none (the three `#coverage` rows cover three), file an `add` delta per topic — `kind open`, `status open`, grade from the pointer of the row that touched it (the mechanism row's jar or run evidence), owner `platform/overview.md#coverage`, claim "The <topic> is touched by rows but has no page: <what the rows establish and what is unread>". An `absent` topic gets no row.
- Sources: `docs/testing/spikes.md` (7), `docs/modding/anatomy.md` (4), `docs/modding/lua-api.md` (4), `docs/modding/wall-map.md` (2), `docs/testing/README.md` (2), `docs/testing/pipeline-design.md` (1); the finished pages for `#routing`.
- Cap 400; run only after Tasks 3–22 are committed; links resolve without `--partial` (run the lint both ways and report).

---

### Task 24: Close (controller)

**Files:**
- Modify: `CLAUDE.md` § 3, § 4, § 6; the memory file `C:\Users\Angus\.claude\projects\C--Users-Angus\memory\pz-nutrition-mod-project.md` and its `MEMORY.md` line; `docs/superpowers/plans/restructure-anchors.md` only if a page split or a cross-page retarget changed an owner (fold the new section or the moved anchor in, so the plan stays the Phase 3 checklist).

- [ ] **Step 1: Gates**

```bash
cd /c/Users/Angus/repos/project_zomboid && python tools/claims_check.py --partial && python tools/page_lint.py docs/platform/*.md docs/facts/*.md docs/facts/other-mods/*.md && grep -rEn '\b(previously|corrected 20|resolved (in|by) slice|RESOLVED 20|CONTESTED|the review found|this slice)\b' docs/platform docs/facts | wc -l && python tools/bus_inventory.py --check && python tools/doc_lint.py docs/mods-survey docs/modding && python tools/doc_lint.py docs/vanilla docs/modding docs/testing references docs/mods-survey/nutrition-mods.md && python -m pytest tools/tests testing/tests -q 2>&1 | tail -1 && git status --short | wc -l && ls .superpowers/sdd/restructure-2-platform-facts/*-delta.tsv 2>/dev/null | wc -l
```

Expected: `0 findings` (rule 4 warnings under `docs/platform` and `docs/facts` listed and counted in the ledger — the target is 0), the page lint `0 findings` with every page's prose count printed, the grep `0`, `in sync`, both lints `0`, tests green (write the number down), a clean tree. Every delta file listed was applied (each has its `Register: task N delta` commit in `git log`); `python tools/claims_check.py` without `--partial` still fails only on `areas/` and `reference/datasets.md` / `reference/tools.md` owners (Phase 3) — count those findings and record them.

- [ ] **Step 2: `CLAUDE.md`**

§ 3: append one paragraph — "Restructure Phase 2 closed <date> (`<first commit>..<last commit>`): `docs/platform/` (8 pages) and `docs/facts/` (7 pages + `other-mods/` 6) written from the register under the page contract; `tools/claims_delta.py` (the delta applier) and `tools/page_lint.py` (the contract as rules); <N> deltas applied (<adds> rows minted, `#2040–#<last>`; <retargets> retargets; <status changes>); the register at <rows> rows; every page lint-clean at <total prose> prose lines." § 4: "Next: write the Phase 3 plan (`docs/superpowers/plans/restructure-3-areas-skills-roots.md`) with `superpowers:writing-plans` from the spec § Execution Phase 3 (the seven area pages and `open-questions.md`, the ten skills, the root `README.md`, `STRATEGY.md` trimmed, `CLAUDE.md` rewritten per § What the rewritten `CLAUDE.md` carries, `reference/datasets.md` and `reference/tools.md`), the anchor plan and `claims_check.py --view areas`; then execute it with SDD." § 6: add `python tools/page_lint.py <the pages touched>` to the gates before any commit that touches `docs/platform`, `docs/facts` or `docs/areas`, and the new test count.

- [ ] **Step 3: Commit, push, memory**

```bash
cd /c/Users/Angus/repos/project_zomboid && git add CLAUDE.md && git commit -m "Restructure 2: close" -- CLAUDE.md && git push origin main && git log --oneline -1 && git status -sb | head -n 1
```

Then update the memory file's status paragraph (Phase 2 closed; the page and delta counts; NEXT = the Phase 3 plan) and the `MEMORY.md` index line.

---

## What the whole-branch review checks

The final reviewer (Opus) reads the spec § The page contract, § The target tree (placement, sync placement, the hard cases) and § Acceptance items 1, 3 and 8, then verifies on the branch:

1. Every `docs/platform/` and `docs/facts/` page exists (21), lint-clean, within its cap, with the anchor plan's anchors in order; `platform/overview.md`'s `## Coverage` and `#routing` reflect the finished pages.
2. `python tools/claims_check.py --partial` → 0 findings; rule 4 warnings under the two layers at or near 0 with every remaining one justified in the ledger; every row owned by a Phase 2 page tagged on it; no page tag names a row the register lacks; every suffix canonical.
3. Twenty tagged sentences sampled across the pages against their rows: the sentence states the claim, with its numbers and its bound where it matters; no number restated off another page's row; every `order` block and `table` verbatim against its old doc.
4. The hard cases: the per-key merge on `loader-and-scripts.md`, the hook dispatch on `lua-platform.md#script-hooks`, the checksum gate on `mod-anatomy.md#checksum-gate`, the registries on `lua-platform.md#registries`, the packet mechanisms on `mp-model.md` and the field contracts on `wire-packets.md` — each stated once, on its owner, and cited elsewhere.
5. Every delta applied by a `Register: task N delta` commit, each `add` resting on evidence the old doc states (a re-located pointer), each `retarget` naming a real anchor, no provisional tag left (`grep -rn '\[T[0-9]' docs/platform docs/facts` empty); the register's post block contiguous through the last minted id; `--register-only` clean.
6. The narrative grep empty; no run id in prose without a tag; no `@offset` in prose; the stamp line on every page.
7. `## Worked examples` paths exist and the shapes are at the cited lines (sample five).
8. Nothing changed under `docs/vanilla`, `docs/modding`, `docs/mods-survey`, `docs/testing`, `testing/` (except nothing), `data/`; the register changed only through delta commits; the tools' tests green at the recorded count.
