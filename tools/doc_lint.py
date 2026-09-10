#!/usr/bin/env python3
"""House-style lint for the reference library (spec: evidence & documentation standard)."""
import argparse, collections, os, re, sys

Finding = collections.namedtuple("Finding", "path line rule detail")
STAMP_RX = re.compile(r"Verified against: 42\.20\.4")
PLACEHOLDER_RX = re.compile(r"\bTODO\b|\bTBD\b|_digest pending_")
STAMPED_DIRS = ("docs/vanilla", "docs/modding", "docs/feasibility", "docs/mods-survey/teardowns")
SKIP_DIRS = ("docs/superpowers", ".superpowers")
SKIP_FILES = ("docs/progress.md", "README.md")
MIRROR_KEYS = ("**Source:**", "**Fetched:**", "**Wiki page version:**", "**License:**")
MIRROR_DIR = "references/wiki-mirrors"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _rel(path, root):
    return os.path.relpath(path, root).replace("\\", "/")

def _under(rel, d):
    """True when `rel` is the directory `d` or something inside it (whole segments only)."""
    return rel == d or rel.startswith(d + "/")

def _tables(lines):
    """Yield (start_line, header_cells, body_rows) for each markdown table."""
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

def lint_file(path, repo_root=None):
    rel = _rel(path, repo_root or REPO_ROOT)
    if any(_under(rel, s) for s in SKIP_DIRS) or any(rel.endswith(s) for s in SKIP_FILES):
        return []
    text = open(path, encoding="utf-8", errors="replace").read()
    lines = text.splitlines()
    out = []
    stamped = any(_under(rel, d) for d in STAMPED_DIRS)
    if stamped and not STAMP_RX.search(text):
        out.append(Finding(rel, 1, "stamp", "missing 'Verified against: 42.20.4'"))
    for n, line in enumerate(lines, 1):
        if PLACEHOLDER_RX.search(line):
            out.append(Finding(rel, n, "placeholder", line.strip()[:80]))
    if stamped:
        m = re.search(r"^## Sources\s*$", text, re.M)
        rest = text[m.end():] if m else ""
        nxt = re.search(r"^## ", rest, re.M)  # the section ends at the next '## ' heading
        body = (rest[:nxt.start()] if nxt else rest).strip()
        if not m or not body:
            out.append(Finding(rel, len(lines), "sources", "missing or empty '## Sources'"))
        for start, header, rows in _tables(lines):
            if "Ev" in header:
                col = header.index("Ev")
                for ln, cells in rows:
                    if col >= len(cells) or not re.search(r"\b[CMW]\b", cells[col]):
                        out.append(Finding(rel, ln + 1, "grades", "row without C/M/W evidence grade"))
    if _under(rel, MIRROR_DIR):
        for key in MIRROR_KEYS:
            if key not in text:
                out.append(Finding(rel, 1, "mirror-header", f"missing {key}"))
    return out

def lint(targets, repo_root=None):
    """Lint every .md under `targets` (directories are walked, files linted directly).

    Rule scoping and reported paths are always relative to `repo_root` (default:
    this repo), never to the target, so narrowing the target cannot turn a rule off.
    """
    repo_root = repo_root or REPO_ROOT
    out = []
    for target in targets:
        if os.path.isfile(target):
            out += lint_file(target, repo_root)
            continue
        if not os.path.isdir(target):
            raise SystemExit(f"doc_lint: no such file or directory: {target}")
        for dirpath, dirs, files in os.walk(target):
            dirs.sort()
            for f in sorted(files):
                if f.endswith(".md"):
                    out += lint_file(os.path.join(dirpath, f), repo_root)
    return out

def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("targets", nargs="*", metavar="target",
                    help="files or directories to lint (default: the whole repo)")
    ap.add_argument("--root", default=REPO_ROOT, metavar="DIR",
                    help="repo root that rule scoping and reported paths are relative to")
    ns = ap.parse_args(argv)
    findings = lint(ns.targets or [ns.root], ns.root)
    for f in findings:
        print(f"{f.path}:{f.line}: {f.rule}: {f.detail}")
    print(f"{len(findings)} finding(s)")
    return 1 if findings else 0

if __name__ == "__main__":
    # Findings quote doc text verbatim; the default Windows console encoding
    # (cp1252) cannot encode em dashes/arrows and would abort the run.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    sys.exit(main(sys.argv[1:]))
