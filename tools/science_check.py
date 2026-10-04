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
