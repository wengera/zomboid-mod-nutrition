#!/usr/bin/env python3
"""House-style lint for the reference library (spec: evidence & documentation standard)."""
import collections, os, re, sys

Finding = collections.namedtuple("Finding", "path line rule detail")
STAMP_RX = re.compile(r"Verified against: 42\.20\.4")
PLACEHOLDER_RX = re.compile(r"\bTODO\b|\bTBD\b|_digest pending_")
STAMPED_DIRS = ("docs/vanilla", "docs/modding", "docs/feasibility", "docs/mods-survey/teardowns")
SKIP_DIRS = ("docs/superpowers",)
SKIP_FILES = ("docs/progress.md", "README.md")
MIRROR_KEYS = ("**Source:**", "**Fetched:**", "**Wiki page version:**", "**License:**")

def _rel(path, root):
    return os.path.relpath(path, root).replace("\\", "/")

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

def lint_file(path, root):
    rel = _rel(path, root)
    if any(rel.startswith(s) for s in SKIP_DIRS) or any(rel.endswith(s) for s in SKIP_FILES):
        return []
    text = open(path, encoding="utf-8", errors="replace").read()
    lines = text.splitlines()
    out = []
    stamped = any(rel.startswith(d) for d in STAMPED_DIRS)
    if stamped and not STAMP_RX.search(text):
        out.append(Finding(rel, 1, "stamp", "missing 'Verified against: 42.20.4'"))
    for n, line in enumerate(lines, 1):
        if PLACEHOLDER_RX.search(line):
            out.append(Finding(rel, n, "placeholder", line.strip()[:80]))
    if stamped:
        m = re.search(r"^## Sources\s*$", text, re.M)
        body = text[m.end():].strip() if m else ""
        if not m or not body:
            out.append(Finding(rel, len(lines), "sources", "missing or empty '## Sources'"))
        for start, header, rows in _tables(lines):
            if "Ev" in header:
                col = header.index("Ev")
                for ln, cells in rows:
                    if col >= len(cells) or not re.search(r"\b[CMW]\b", cells[col]):
                        out.append(Finding(rel, ln + 1, "grades", "row without C/M/W evidence grade"))
    if "references/wiki-mirrors/" in rel:
        for key in MIRROR_KEYS:
            if key not in text:
                out.append(Finding(rel, 1, "mirror-header", f"missing {key}"))
    return out

def lint(roots):
    out = []
    for root in roots:
        for dirpath, _, files in os.walk(root):
            for f in files:
                if f.endswith(".md"):
                    out += lint_file(os.path.join(dirpath, f), root)
    return out

if __name__ == "__main__":
    # Findings quote doc text verbatim; the default Windows console encoding
    # (cp1252) cannot encode em dashes/arrows and would abort the run.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    roots = sys.argv[1:] or [repo]
    findings = lint(roots)
    for f in findings:
        print(f"{f.path}:{f.line}: {f.rule}: {f.detail}")
    print(f"{len(findings)} finding(s)")
    sys.exit(1 if findings else 0)
