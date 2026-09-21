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
# The remedial clause runs to the end of its sentence: a `.` only ends it when a space or the
# end of the cell follows, so the dots inside a key like `rows.r12_weight_bands` are kept.
READ_INSTEAD_RX = re.compile(r"((?:read|use|take|cite)\b(?:[^.;]|\.(?=\S))*)", re.I)
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
                    value = cells[1] if len(cells) > 1 else ""
                    why = cells[2] if len(cells) > 2 else ""
                    keys, prose = re.findall(r"`([^`]+)`", cells[0]), ""
                    if not keys:
                        # A Key cell that names no key is a prose restriction of the same shape
                        # as a bullet ("everything measured here, as a population"): it scopes the
                        # whole file, so the key is `*` and the prose joins the reason. A bare
                        # one-word cell is an unbackticked key, and stays a key.
                        keys, prose = ([cells[0]], "") if cells[0] and " " not in cells[0] else (["*"], cells[0])
                    for key in keys:
                        row = _dnc(run, key, value, why)
                        if prose:
                            row["why"] = _clean(prose + " — " + why)
                        out.append(row)
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
