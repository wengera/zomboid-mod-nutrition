#!/usr/bin/env python3
"""The page lint: the page contract (spec § The page contract) for docs/areas, docs/platform, docs/facts.

Per page: the stamp line; the section set and order for its layer; the <a id> anchors (every register
row owned by the page has its anchor on the page; no duplicate); a `## Rules` line has a colon and ends
with a tag, a `## Key facts` line ends with a tag; `## Walls and bounds` ends with a "Not covered:"
line; no narrative marker outside code spans; the prose line count against the cap (over the cap
fails; under 150 warns; tables, fences, headings, anchor lines and `## Open` index rows do not count);
every `## Worked examples` path exists; every relative link resolves to a page and, when it carries a
fragment, that fragment is a lowercase slug and — on a page of the three layers, the only ones the
contract gives `<a id>` anchors — an anchor on it (--partial skips a missing page). Exit 1 on a finding;
a warning never fails.

Usage: python tools/page_lint.py <page.md> [...] [--partial] [--register TSV] [--cap N] [--root DIR]"""
import argparse, collections, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claimslib as cl

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = "docs/reference/claims.tsv"
STAMP_RX = re.compile(r"^Verified against 42\.20\.4 \(b0bbce05d5\) · \d{4}-\d{2}-\d{2} · scope: \S.*$")
# The spec's marker list; its closing boundary is `(?![A-Za-z])`, not `\b`, so that the dated
# markers match the date that follows them (`\b` fails between the `20` and the `26`).
NARRATIVE_RX = re.compile(r"\b(previously|corrected 20|resolved (in|by) slice|RESOLVED 20|CONTESTED|the review found|this slice)(?![A-Za-z])")
CODE_SPAN_RX = re.compile(r"`[^`]*`")
ANCHOR_RX = re.compile(r'^<a id="([a-z0-9-]+)"></a>\s*$')
# Any fragment, not only a well-formed one: a link whose fragment the contract would reject must
# still have its target checked, and the fragment shape is a finding of its own.
LINK_RX = re.compile(r"\]\(([^)\s#]*)(#[^)\s]*)?\)")
FRAGMENT_RX = re.compile(r"^[a-z0-9-]+$")
FILE_LINES_RX = re.compile(r"([A-Za-z0-9_./-]+\.[A-Za-z0-9]+):\d+(?:[-–]\d+)?")
TABLE_SEP_RX = re.compile(r"^\|\s*:?-")
# A trailing `?` marks an optional section; the order is the contract's.
SECTIONS = {
    "platform": ["Rules", "How it works", "Walls and bounds", "Open", "Worked examples?", "Procedure?", "See also"],
    "facts": ["Key facts", "How it works", "Walls and bounds", "Open", "Worked examples?", "See also"],
    "areas": ["Rules", "How it works", "Options", "Walls and bounds", "Open", "Worked examples?", "See also"],
}
PAGE_SECTIONS = {"platform/overview.md": ["Rules", "How it works", "Coverage", "Open", "Worked examples?", "See also"]}
# Only these layers are under the page contract, so only they carry `<a id>` anchors: a link into
# docs/reference/ or an old doc is checked for its page, never for its fragment.
CONTRACT_LAYERS = ("areas", "platform", "facts")
CAPS = {"platform/harness.md": 500, "platform/mod-anatomy.md": 500, "platform/lua-platform.md": 500, "platform/mp-model.md": 500}
DEFAULT_CAP, FLOOR = 400, 150
WARN_RULES = ("prose-floor",)
Finding = collections.namedtuple("Finding", "path line rule detail")


def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read().replace("\r\n", "\n")


def _sections(lines):
    """[(heading or '', [(n, line), ...])] split on `## ` headings; the preamble has heading ''.

    A `## ` line inside a fence is quoted markdown, not a heading: it stays in the section it is
    written in, so a page that quotes the contract does not grow a phantom section (and does not
    lose the tail of the section the quote sits in)."""
    out, cur, fence = [], ("", []), False
    for n, line in enumerate(lines, 1):
        if line.startswith("```"):
            fence = not fence
        elif line.startswith("## ") and not fence:
            out.append(cur); cur = (line[3:].strip(), [])
            continue
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
        # A table's header row is the row a separator row follows, whatever its first cell reads.
        header_rows = set()
        if heading == "Worked examples":
            for i, (n, line) in enumerate(body):
                nxt = body[i + 1][1].strip() if i + 1 < len(body) else ""
                if line.strip().startswith("|") and TABLE_SEP_RX.match(nxt):
                    header_rows.add(n)
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
            if (heading == "Worked examples" and stripped.startswith("|")
                    and not TABLE_SEP_RX.match(stripped) and n not in header_rows):
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                if len(cells) >= 2:
                    m = FILE_LINES_RX.search(cells[1])
                    if not m:
                        out.append(Finding(rel, n, "example", "no file:lines cell: %s" % cells[1]))
                    elif not os.path.exists(os.path.join(root, *m.group(1).split("/"))):
                        out.append(Finding(rel, n, "example", "worked example path does not exist: %s" % cells[1]))
            for m in LINK_RX.finditer(line):
                target, anchor = m.group(1), m.group(2)
                if target.startswith(("http://", "https://")) or (not target and not anchor):
                    continue
                if anchor and not FRAGMENT_RX.match(anchor[1:]):
                    out.append(Finding(rel, n, "link", "fragment must be a lowercase slug: %s%s" % (target, anchor)))
                    anchor = None
                tpath = os.path.normpath(os.path.join(os.path.dirname(path), target)) if target else path
                if not os.path.exists(tpath):
                    if not partial:
                        out.append(Finding(rel, n, "link", "link target does not exist: %s" % target))
                    continue
                if (anchor and tpath.endswith(".md") and _page_key(tpath, root).split("/")[0] in CONTRACT_LAYERS
                        and ('<a id="%s">' % anchor[1:]) not in _read(tpath)):
                    out.append(Finding(rel, n, "link", "link anchor not found: %s%s" % (target, anchor)))
            if (not stripped or stripped.startswith("#") or stripped.startswith("|") or ANCHOR_RX.match(stripped)
                    or heading == "Open" or (heading == "" and n <= 2)):
                continue
            prose += 1
        if heading == "Walls and bounds":
            tail = [l for _, l in body if l.strip()]
            if not tail or not tail[-1].startswith("Not covered:"):
                out.append(Finding(rel, body[-1][0] if body else 1, "walls", "'## Walls and bounds' must end with a"
                                   " 'Not covered:' line (a stray <a id> above the next heading counts as the last line)"))
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
