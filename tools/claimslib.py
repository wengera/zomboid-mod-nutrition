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

ID_RX = re.compile(r"#\d{4}(?!\d)")
ID_FULL_RX = re.compile(r"^#\d{4}$")
_ID_ITEM = r"#\d{4}(?!\d)(?:/[^\]\[,\s]+)*"
_PROV_ITEM = r"T\d+\.\d+"
_TAG_ITEM = r"(?:" + _ID_ITEM + r"|" + _PROV_ITEM + r")"
# A tag bracket is a comma-separated list of items, each a claim id with its optional
# suffixes or a provisional T<n>.<m>, and it must carry at least one real id: that keeps
# `[T3.7]` alone a provisional marker while `[#0231/M, T3.7]` is a mixed tag.
TAG_RX = re.compile(r"\[(?=[^\]\[]*#\d{4})(" + _TAG_ITEM + r"(?:,\s*" + _TAG_ITEM + r")*)\]")
PROVISIONAL_RX = re.compile(r"\[T\d+\.\d+\]")
PROVISIONAL_ID_RX = re.compile(r"^" + _PROV_ITEM + r"$")
BRACKET_RX = re.compile(r"\[([^\]\[]*)\]")
OWNER_RX = re.compile(r"^(areas|platform|facts|reference)/[A-Za-z0-9._/-]+\.md#[a-z0-9-]+$")
BOUND_N_RX = re.compile(r"^n=\d+$")
BOUND_SEP_RX = re.compile(r"[\s;,:]")
ANCHOR_RX = re.compile(r'"[^"]+"')
# lua / mod / repo pointers read `<path>:<line>[-<line>] "<anchor text>"` and nothing else.
ANCHORED_PTR_RX = re.compile(r'^[^\s"]+:\d+(?:[-–]\d+)?\s+' + ANCHOR_RX.pattern + r"$")
RUN_ID_RX = re.compile(r"^[a-z0-9]+-\d{8}-\d{6}(?:\s|$)")


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
                if "\t" in c or "\n" in c or "\r" in c:
                    raise RegisterError("%s: a cell contains a tab, CR or newline: %r" % (r.get("id"), c[:60]))
            f.write("\t".join(cells) + "\n")


def _split_outside_quotes(cell, sep=";"):
    """Split on `sep` only where it is not inside double-quoted anchor text."""
    parts, buf, quoted = [], [], False
    for ch in cell:
        if ch == '"':
            quoted = not quoted
            buf.append(ch)
        elif ch == sep and not quoted:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return parts


def parse_pointers(cell):
    """'jar:X @1 L2; run:id file key' -> [('jar', 'X @1 L2'), ('run', 'id file key')].

    The `;` separator is honoured only outside quoted anchor text, so a Lua anchor may
    contain one. An empty payload is a ValueError: a form with nothing after it is not
    a pointer."""
    out = []
    for part in [p.strip() for p in _split_outside_quotes(cell) if p.strip()]:
        form, sep, text = part.partition(":")
        form = form.strip()
        if not sep or form not in POINTER_FORMS:
            raise ValueError("unknown pointer form in %r" % part)
        text = text.strip()
        if not text:
            raise ValueError("pointer %r has an empty payload" % part)
        out.append((form, text))
    return out


def strongest_grade(forms):
    grades = []
    for f in forms:
        if f not in POINTER_FORMS:
            raise ValueError("unknown pointer form %r" % f)
        grades.append(POINTER_FORMS[f])
    return max(grades, key=lambda g: GRADE_RANK[g]) if grades else "C"


def parse_bound(cell):
    """('none', '') for empty; else (token, rest). Raises ValueError on an unknown first token.

    The token may be closed by a space, `;`, `,` or `:`; `rest` is what follows with the
    leading separators and spaces stripped."""
    cell = cell.strip()
    if not cell:
        return ("none", "")
    m = BOUND_SEP_RX.search(cell)
    token, rest = (cell[:m.start()], cell[m.start():]) if m else (cell, "")
    if token in BOUND_TOKENS or BOUND_N_RX.match(token):
        return (token, rest.lstrip(" \t;,:").strip())
    raise ValueError("bound must start with a controlled token, got %r" % token)


def canonical_suffix(row):
    token, _ = parse_bound(row.get("bound", ""))
    grade, status = row.get("grade", "C"), row.get("status", "settled")
    if grade == "C" and token == "none" and status == "settled":
        return ""
    parts = [grade]
    if token != "none":
        parts.append(token)
    if status != "settled":
        parts.append(status)
    return "/" + "/".join(parts)


def is_provisional(cid):
    """True for a provisional marker id like 'T3.7'."""
    return bool(PROVISIONAL_ID_RX.match(cid))


def find_provisional(text):
    """Every provisional marker in `text`: `[T3.7]` alone and `T3.7` inside a mixed tag."""
    out = []
    for m in BRACKET_RX.finditer(text):
        for item in [i.strip() for i in m.group(1).split(",")]:
            if is_provisional(item):
                out.append(item)
    return out


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
            if form == "run" and not RUN_ID_RX.match(text):
                errs.append("run: pointer must start with a run id: %r" % text[:50])
            if form in ANCHORED_FORMS and not ANCHORED_PTR_RX.match(text):
                errs.append('%s: pointer must read <path>:<line> "anchor text": %r' % (form, text[:50]))
    except ValueError as e:
        errs.append(str(e))
    try:
        token, _ = parse_bound(row.get("bound", ""))
        if token == "inference" and row.get("grade") == "M":
            errs.append("grade M on an inference bound: an inference is never measured")
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
    owner = row.get("owner", "").strip()
    if owner and not OWNER_RX.match(owner):
        errs.append("owner %r is not <layer>/<page>.md#<anchor>" % owner)
    if not owner and row.get("status") != "superseded":
        errs.append("owner is empty")
    return errs
