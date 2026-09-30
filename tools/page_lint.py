#!/usr/bin/env python3
"""The page lint: the page contract (spec § The page contract) for docs/areas, docs/platform, docs/facts,
and a reference profile for the two tagged reference pages.

Per page: the stamp line; the section set and order for its layer (two pages carry their own set:
platform/overview.md, and areas/open-questions.md with Index, Decisions, Experiments, See also); the
<a id> anchors (every register row owned by the page has its anchor on the page; no duplicate); a
`## Rules` line has a colon and ends with a tag, a `## Key facts` line ends with a tag; `## Walls and
bounds` ends with a "Not covered:" line; no narrative marker outside code spans; the prose line count
against the cap (over the cap fails; under 150 warns, except on facts/other-mods/ pages, whose Key
facts are one line per technique, and on areas/open-questions.md, whose index is rows; tables, fences,
headings, anchor lines and `## Open` index rows do not count); every `## Worked examples` path exists;
every relative link resolves to a page; a fragment must be a lowercase slug (`a-z`, `0-9`, `-`, `_`), and
a fragment into a page of the three layers or into one of the three tagged reference pages (datasets.md,
tools.md, wall-map.md) must name an `<a id>` on it (--partial skips a missing page). On areas/open-questions.md every
`open` register row must carry a tag somewhere on the page (open-index). The reference profile
(reference/datasets.md, reference/tools.md: tagged owners outside the contract's section shape) checks
the stamp, the anchors, the narrative markers and the links only: no section set, rule lines, walls,
worked examples, cap or floor. reference/wall-map.md is in REFERENCE_PAGES so that a fragment into it
is checked like one into datasets.md or tools.md; it is a link target only, never a page this lint is
passed (doc_lint owns it), though the reference profile would run on it if it were. Exit 1 on a
finding; a warning never fails. `--allow-provisional` lets a `## Rules` or `## Key facts` line end in a
provisional `[T<task>.<n>]` tag while a wave's deltas are unapplied.

Usage: python tools/page_lint.py <page.md> [...] [--partial] [--allow-provisional] [--register TSV] [--cap N] [--root DIR]"""
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
FRAGMENT_RX = re.compile(r"^[a-z0-9_-]+$")
FILE_LINES_RX = re.compile(r"([A-Za-z0-9_./-]+\.[A-Za-z0-9]+):\d+(?:[-–]\d+)?")
TABLE_SEP_RX = re.compile(r"^\|\s*:?-")
# A trailing `?` marks an optional section; the order is the contract's.
SECTIONS = {
    "platform": ["Rules", "How it works", "Walls and bounds", "Open", "Worked examples?", "Procedure?", "See also"],
    "facts": ["Key facts", "How it works", "Walls and bounds", "Open", "Worked examples?", "See also"],
    "areas": ["Rules", "How it works", "Options", "Walls and bounds", "Open", "Worked examples?", "See also"],
}
PAGE_SECTIONS = {
    "platform/overview.md": ["Rules", "How it works", "Coverage", "Open", "Worked examples?", "See also"],
    "areas/open-questions.md": ["Index", "Decisions", "Experiments", "See also"],
}
# Tagged owners outside the contract's section shape; wall-map.md is a fragment-checked link target only.
REFERENCE_PAGES = ("reference/datasets.md", "reference/tools.md", "reference/wall-map.md")
NO_FLOOR = ("facts/other-mods/", "areas/open-questions.md")           # the mod pages' Key facts are one line per technique; the index is rows
OPEN_INDEX = "areas/open-questions.md"
# Only these layers are under the page contract, so only they carry `<a id>` anchors: a link into
# docs/reference/ or an old doc is checked for its page only, except the three tagged reference pages (REFERENCE_PAGES),
# whose <a id> anchors are checked like a contract page's.
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


def lint(path, root=REPO_ROOT, register=None, partial=False, cap=None, allow_provisional=False):
    rel = os.path.relpath(path, root).replace("\\", "/")
    key = _page_key(path, root)
    layer = key.split("/")[0]
    reference = key in REFERENCE_PAGES
    text = _read(path)
    lines = text.split("\n")
    out = []
    # stamp
    if len(lines) < 2 or not STAMP_RX.match(lines[1]):
        out.append(Finding(rel, 2, "stamp", "line 2 must read 'Verified against 42.20.4 (b0bbce05d5) · <date> · scope: <one line>'"))
    # sections (a reference page has no contract section shape)
    secs = _sections(lines)
    if not reference:
        spec = PAGE_SECTIONS.get(key) or SECTIONS.get(layer, SECTIONS["facts"])
        names = [s.rstrip("?") for s in spec]
        required = [s for s in spec if not s.endswith("?")]
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
    rows = cl.read_register(reg_path) if os.path.exists(reg_path) else []
    for r in rows:
        page, _, anchor = r["owner"].partition("#")
        if page == key and r["status"] != "superseded" and anchor and anchor not in seen:
            out.append(Finding(rel, 1, "anchor", "%s is owned by #%s but the page has no <a id=\"%s\">" % (r["id"], anchor, anchor)))
    # the open index: every open row, whichever page owns it, carries a tag on this page
    if key == OPEN_INDEX:
        tagged = {cid for _, cid, _ in cl.iter_tags(text)}
        for r in rows:
            if r["status"] == "open" and r["id"] not in tagged:
                out.append(Finding(rel, 1, "open-index", "%s (%s) is open but not indexed on this page" % (r["id"], r["owner"])))
    # section bodies
    rule_tag_rx = r"\[(?:#\d{4}|T\d+\.\d+)[^\]]*\]\.?\s*$" if allow_provisional else r"\[#\d{4}[^\]]*\]\.?\s*$"
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
            if not reference and heading in ("Rules", "Key facts") and stripped.startswith("- "):
                if not re.search(rule_tag_rx, stripped):
                    out.append(Finding(rel, n, "rule-line", "a %s line must end with its tag: %s" % (heading, stripped[:60])))
                elif heading == "Rules" and ": " not in stripped:
                    out.append(Finding(rel, n, "rule-line", "a rule line is '<imperative>: <reason> [#tag]': %s" % stripped[:60]))
            bare = CODE_SPAN_RX.sub("", line)
            if NARRATIVE_RX.search(bare):
                out.append(Finding(rel, n, "narrative", "narrative marker: %s" % stripped[:60]))
            if (not reference and heading == "Worked examples" and stripped.startswith("|")
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
                if (anchor and tpath.endswith(".md") and (_page_key(tpath, root).split("/")[0] in CONTRACT_LAYERS or _page_key(tpath, root) in REFERENCE_PAGES)
                        and ('<a id="%s">' % anchor[1:]) not in _read(tpath)):
                    out.append(Finding(rel, n, "link", "link anchor not found: %s%s" % (target, anchor)))
            if (not stripped or stripped.startswith("#") or stripped.startswith("|") or ANCHOR_RX.match(stripped)
                    or heading == "Open" or (heading == "" and n <= 2)):
                continue
            prose += 1
        if not reference and heading == "Walls and bounds":
            tail = [l for _, l in body if l.strip()]
            if not tail or not tail[-1].startswith("Not covered:"):
                out.append(Finding(rel, body[-1][0] if body else 1, "walls", "'## Walls and bounds' must end with a"
                                   " 'Not covered:' line (a stray <a id> above the next heading counts as the last line)"))
    if reference:
        return out, prose                     # counted, never capped or floored
    limit = cap or CAPS.get(key, DEFAULT_CAP)
    if prose > limit:
        out.append(Finding(rel, 1, "prose", "%d prose lines, cap %d" % (prose, limit)))
    elif prose < FLOOR and not key.startswith(NO_FLOOR):
        out.append(Finding(rel, 1, "prose-floor", "%d prose lines, under the 150 the contract expects" % prose))
    return out, prose


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pages", nargs="+"); ap.add_argument("--root", default=REPO_ROOT); ap.add_argument("--register")
    ap.add_argument("--partial", action="store_true"); ap.add_argument("--cap", type=int)
    ap.add_argument("--allow-provisional", action="store_true")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    findings = []
    for p in a.pages:
        f, prose = lint(os.path.abspath(p), root=os.path.abspath(a.root), register=a.register, partial=a.partial, cap=a.cap,
                        allow_provisional=a.allow_provisional)
        findings += f
        key = _page_key(os.path.abspath(p), os.path.abspath(a.root))
        limit = "no cap" if key in REFERENCE_PAGES else "cap %d" % (a.cap or CAPS.get(key, DEFAULT_CAP))
        print("%s: prose %d lines (%s)" % (os.path.relpath(p, a.root).replace("\\", "/"), prose, limit))
    for f in sorted(findings, key=lambda f: (f.path, f.line, f.rule)):
        print("%s:%d: %s: %s%s" % (f.path, f.line, f.rule, f.detail, " (warning)" if f.rule in WARN_RULES else ""))
    n_err = sum(1 for f in findings if f.rule not in WARN_RULES)
    print("%d findings, %d warnings" % (n_err, len(findings) - n_err))
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
