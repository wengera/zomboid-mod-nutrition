#!/usr/bin/env python3
"""Generated sections of the reference (spec § The target tree): the artifacts register's `Cited by`
column and the wiki mirrors' contradiction table, rendered from the register.

    python tools/reference_gen.py cited-by [--page docs/reference/artifacts.md] [--write | --check]
    python tools/reference_gen.py contradictions [--readme references/wiki-mirrors/README.md] [--write | --check]

cited-by: for every row of the page's `## Contents` table, the `Cited by` cell lists the owner pages
of the live rows whose pointer carries `run:<run id>` (aliases from docs/reference/run-aliases.csv
count for both ids), sorted, deduplicated, as links relative to docs/reference/; `—` when none.
contradictions: one table per mirror file in the README's `## Mirrors` order, from the live
`contradiction` rows whose `wiki:` pointer names the file, between the markers
`<!-- reference_gen: contradictions start -->` / `<!-- reference_gen: contradictions end -->`.
--check exits 1 and names each drift; --write rewrites only the generated cells or section."""
import argparse, collections, csv, io, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claimslib as cl

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = "docs/reference/claims.tsv"
ALIASES = "docs/reference/run-aliases.csv"
ARTIFACTS_PAGE = "docs/reference/artifacts.md"
MIRRORS_README = "references/wiki-mirrors/README.md"
START = "<!-- reference_gen: contradictions start -->"
END = "<!-- reference_gen: contradictions end -->"
NONE_CELL = "—"
MIRROR_WRONG = "mirror wrong:"
# A cell boundary is a `|` that is not escaped as `\|`.
PIPE_RX = re.compile(r"(?<!\\)\|")
TABLE_SEP_RX = re.compile(r"^\|\s*:?-")
RUN_ID_IN_CELL_RX = re.compile(r"[a-z0-9]+-\d{8}-\d{6}")
CONTRADICTIONS_INTRO = (
    "Generated from [the claims register](../../docs/reference/claims.tsv) by "
    "`python tools/reference_gen.py contradictions --write`; never edit it by hand: "
    "`python tools/claims_check.py` fails when it drifts. Each table is one mirror, in the "
    "`## Mirrors` order, and lists every live register row of kind `contradiction` whose `wiki:` "
    "pointer names that mirror: the row's tag, what the code says (the row's claim), what the "
    "mirror says (the words its bound quotes after `mirror wrong:`), and the page that owns the row."
)


# ---- shared helpers -------------------------------------------------------------------------

def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def _cell(text):
    """A table cell's text with a literal `|` escaped."""
    return text.replace("|", "\\|")


def _live(row):
    return row.get("status") != "superseded"


def _arms(pointer, form):
    """The payloads of the pointer's `<form>:` arms: the segments (split on `;`, stripped) that
    start `<form>:`, with that prefix removed."""
    out = []
    for seg in [s.strip() for s in pointer.split(";")]:
        if seg.startswith(form + ":"):
            out.append(seg[len(form) + 1:].strip())
    return out


def _lines(text):
    """[(body, eol)] with each line's own ending kept ('\\n', '\\r\\n', or '' on the last piece)."""
    pieces, out = text.split("\n"), []
    for i, piece in enumerate(pieces):
        if i == len(pieces) - 1:
            out.append((piece, ""))
        elif piece.endswith("\r"):
            out.append((piece[:-1], "\r\n"))
        else:
            out.append((piece, "\n"))
    return out


def _section_span(bodies, heading):
    """(first, end) line indexes of the body under `## <heading>`, or None when absent."""
    start = None
    for i, b in enumerate(bodies):
        if start is None:
            if b.rstrip() == "## " + heading:
                start = i + 1
        elif b.startswith("## "):
            return start, i
    return (start, len(bodies)) if start is not None else None


def _first_table(bodies, span):
    """(header index, [(row index, row body)]) of the first table inside `span`, or None."""
    lo, hi = span
    for i in range(lo, hi - 1):
        if bodies[i].lstrip().startswith("|") and TABLE_SEP_RX.match(bodies[i + 1].strip()):
            rows, j = [], i + 2
            while j < hi and bodies[j].lstrip().startswith("|"):
                rows.append((j, bodies[j])); j += 1
            return i, rows
    return None


def _cells(body):
    """'| a | b |' -> [' a ', ' b '] (raw, unstripped; an escaped `\\|` stays inside its cell)."""
    segs = PIPE_RX.split(body.strip())
    return segs[1:-1] if len(segs) >= 2 else segs


# ---- cited-by -------------------------------------------------------------------------------

def _aliases(aliases_csv_text):
    """{alias run id: real run id} from run-aliases.csv text (`alias,run,file,key`)."""
    out = {}
    for r in csv.DictReader(io.StringIO(aliases_csv_text or "")):
        alias, run = (r.get("alias") or "").strip(), (r.get("run") or "").strip()
        if alias and run:
            out[alias] = run
    return out


def _cited(rows, aliases):
    """{run id: {owner page}} over the live rows' `run:` arms; an alias counts for its real run too."""
    out = collections.defaultdict(set)
    for r in rows:
        page = r.get("owner", "").split("#")[0].strip()
        if not _live(r) or not page:
            continue
        for payload in _arms(r.get("pointer", ""), "run"):
            toks = payload.split()
            if not toks:
                continue
            out[toks[0]].add(page)
            if toks[0] in aliases:
                out[aliases[toks[0]]].add(page)
    return out


def _render_cited(pages):
    if not pages:
        return NONE_CELL
    return ", ".join("[`%s`](../%s)" % (_cell(p), p) for p in sorted(pages))


def _contents(text):
    """(lines, run-id column, cited-by column, [(line index, run id, raw cells)]) of the page's
    `## Contents` table. Raises ValueError when the page has no such table."""
    lines = _lines(text)
    bodies = [b for b, _ in lines]
    span = _section_span(bodies, "Contents")
    table = _first_table(bodies, span) if span else None
    if table is None:
        raise ValueError("no table under '## Contents'")
    head, rows = table
    header = [c.strip() for c in _cells(bodies[head])]
    if "Run id" not in header or "Cited by" not in header:
        raise ValueError("the '## Contents' table has no 'Run id' and 'Cited by' columns: %s" % " | ".join(header))
    rid, cby = header.index("Run id"), header.index("Cited by")
    out = []
    for i, body in rows:
        cells = _cells(body)
        raw = cells[rid].strip() if rid < len(cells) else ""
        m = RUN_ID_IN_CELL_RX.search(raw)
        out.append((i, m.group(0) if m else raw.strip("`* "), cells))
    return lines, rid, cby, out


def cited_by_cells(page_text, rows, aliases_csv_text):
    """{run id: the rendered `Cited by` cell} for every row of the page's `## Contents` table."""
    _, _, _, table = _contents(page_text)
    cited = _cited(rows, _aliases(aliases_csv_text))
    return {run: _render_cited(cited.get(run, ())) for _, run, _ in table}


def _aliases_text(aliases_path):
    path = aliases_path or os.path.join(REPO_ROOT, *ALIASES.split("/"))
    return _read(path) if os.path.exists(path) else ""


def cited_by_check(page_path, rows, aliases_path=None):
    """One line per `Cited by` cell that differs from the register's render; [] when in sync."""
    text = _read(page_path)
    try:
        _, _, cby, table = _contents(text)
    except ValueError as e:
        return [str(e)]
    want = cited_by_cells(text, rows, _aliases_text(aliases_path))
    out = []
    for i, run, cells in table:
        have = cells[cby].strip() if cby < len(cells) else ""
        if have != want[run]:
            out.append("line %d: %s: Cited by is not the register's render; it should read: %s" % (i + 1, run, want[run]))
    return out


def cited_by_write(page_path, rows, aliases_path=None):
    """Rewrite every drifted `Cited by` cell in place; nothing else on the page changes. Returns
    the number of cells rewritten."""
    text = _read(page_path)
    lines, _, cby, table = _contents(text)
    want = cited_by_cells(text, rows, _aliases_text(aliases_path))
    changed = 0
    for i, run, _ in table:
        body, eol = lines[i]
        segs = PIPE_RX.split(body)
        # segs[0] is what precedes the leading `|`; cell k is segs[k + 1]; pad a short row.
        while len(segs) < cby + 3:
            segs.insert(len(segs) - 1, " ")
        if segs[cby + 1].strip() != want[run]:
            segs[cby + 1] = " %s " % want[run]
            lines[i] = ("|".join(segs), eol)
            changed += 1
    if changed:
        _write(page_path, "".join(b + e for b, e in lines))
    return changed


# ---- contradictions -------------------------------------------------------------------------

def _mirror_files(readme_text):
    """The `File` column of the README's `## Mirrors` table, in its order, backticks removed."""
    bodies = [b for b, _ in _lines(readme_text)]
    span = _section_span(bodies, "Mirrors")
    table = _first_table(bodies, span) if span else None
    if table is None:
        return []
    head, rows = table
    header = [c.strip() for c in _cells(bodies[head])]
    if "File" not in header:
        return []
    k, out = header.index("File"), []
    for _, body in rows:
        cells = _cells(body)
        f = cells[k].strip().strip("`").strip() if k < len(cells) else ""
        if f and f not in out:
            out.append(f)
    return out


def _names(path, mirror):
    return path == mirror or path.endswith("/" + mirror)


def _wiki_files(row):
    return [p.split()[0] for p in _arms(row.get("pointer", ""), "wiki") if p.split()]


def _contradiction_rows(rows):
    live = [r for r in rows if _live(r) and r.get("kind") == "contradiction"]
    return sorted(live, key=lambda r: r.get("id", ""))


def _tag(row):
    """The row's full tag; a bound the register cannot parse is a rule-0 finding, not a crash here."""
    try:
        return "[%s%s]" % (row["id"], cl.canonical_suffix(row))
    except ValueError:
        return "[%s]" % row["id"]


def _mirror_words(row):
    bound = row.get("bound", "")
    i = bound.find(MIRROR_WRONG)
    words = bound[i + len(MIRROR_WRONG):].strip() if i >= 0 else ""
    return words or NONE_CELL


def contradictions_render(readme_text, rows):
    """The `## Contradictions` section (no markers), LF line endings, ending with a newline."""
    live = _contradiction_rows(rows)
    out = ["## Contradictions", "", CONTRADICTIONS_INTRO]
    for mirror in _mirror_files(readme_text):
        mine = [r for r in live if any(_names(f, mirror) for f in _wiki_files(r))]
        if not mine:
            continue
        out += ["", "### " + mirror, "", "| Row | The code says | The mirror says | Owner |", "|---|---|---|---|"]
        for r in mine:
            page = r.get("owner", "").split("#")[0]
            out.append("| %s | %s | %s | [`%s`](../../docs/%s) |" % (
                _tag(r), _cell(r.get("claim", "").strip()), _cell(_mirror_words(r)),
                _cell(page), r.get("owner", "")))
    return "\n".join(out) + "\n"


def _unlisted(readme_text, rows):
    """A line per live contradiction row whose `wiki:` arms name no mirror in `## Mirrors`: the
    render would drop it silently."""
    mirrors = _mirror_files(readme_text)
    out = []
    for r in _contradiction_rows(rows):
        files = _wiki_files(r)
        if files and not any(_names(f, m) for f in files for m in mirrors):
            out.append("%s: its wiki: pointer names %s, which is not in the README's '## Mirrors' table" % (r["id"], ", ".join(files)))
    return out


def has_markers(readme_text):
    return START in readme_text or END in readme_text


def _marker_span(text):
    """(start of START, index of END) or None when the markers are not a start/end pair."""
    s = text.find(START)
    e = text.find(END, s + len(START)) if s >= 0 else -1
    return (s, e) if s >= 0 and e >= 0 else None


def contradictions_check(readme_path, rows):
    """One line per drift: the section is missing, a marker is missing, the section differs from
    the render, or a row names a mirror the README does not list. [] when in sync."""
    text = _read(readme_path)
    if not has_markers(text):
        return ["section missing: no %s / %s markers; run python tools/reference_gen.py contradictions --write" % (START, END)]
    span = _marker_span(text)
    if span is None:
        return ["markers malformed: %s must precede %s, once each" % (START, END)]
    s, e = span
    out = []
    if text[s + len(START):e].replace("\r\n", "\n") != "\n" + contradictions_render(text, rows):
        out.append("drift: the Contradictions section is not the register's render; "
                   "run python tools/reference_gen.py contradictions --write")
    return out + _unlisted(text, rows)


def contradictions_write(readme_path, rows):
    """Write the section between the markers (appended at the end of the README when absent),
    in the README's own line ending. Returns True when the file changed."""
    text = _read(readme_path)
    nl = "\r\n" if "\r\n" in text else "\n"
    block = START + nl + contradictions_render(text, rows).replace("\n", nl) + END
    if not has_markers(text):
        lead = "" if not text else (nl if text.endswith("\n") else nl + nl)
        new = text + lead + block + nl
    else:
        span = _marker_span(text)
        if span is None:
            raise ValueError("markers malformed: %s must precede %s, once each" % (START, END))
        s, e = span
        new = text[:s] + block + text[e + len(END):]
    if new != text:
        _write(readme_path, new)
    return new != text


# ---- CLI ------------------------------------------------------------------------------------

def _utf8_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, opt, default in (("cited-by", "--page", ARTIFACTS_PAGE), ("contradictions", "--readme", MIRRORS_README)):
        p = sub.add_parser(name)
        p.add_argument(opt, default=os.path.join(REPO_ROOT, *default.split("/")))
        mode = p.add_mutually_exclusive_group()
        mode.add_argument("--write", action="store_true"); mode.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    _utf8_console()
    path = os.path.abspath(a.page if a.cmd == "cited-by" else a.readme)
    if not os.path.exists(path):
        print("%s: no such file" % path); return 2
    try:
        rows = cl.read_register(os.path.join(REPO_ROOT, *REGISTER.split("/")))
    except (cl.RegisterError, OSError) as e:
        print(e); return 2
    aliases = os.path.join(REPO_ROOT, *ALIASES.split("/"))
    try:
        if a.cmd == "cited-by":
            if a.check:
                drift = cited_by_check(path, rows, aliases)
            elif a.write:
                print("%d cells rewritten" % cited_by_write(path, rows, aliases)); return 0
            else:
                for run, cell in cited_by_cells(_read(path), rows, _aliases_text(aliases)).items():
                    print("%s\t%s" % (run, cell))
                return 0
        else:
            if a.check:
                drift = contradictions_check(path, rows)
            elif a.write:
                print("section %s" % ("rewritten" if contradictions_write(path, rows) else "unchanged"))
                return 0
            else:
                sys.stdout.write(contradictions_render(_read(path), rows)); return 0
    except ValueError as e:
        print("%s: %s" % (path, e)); return 2
    for d in drift:
        print(d)
    print("%d drifted" % len(drift) if drift else "in sync")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
