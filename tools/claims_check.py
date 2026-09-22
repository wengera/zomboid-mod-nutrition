#!/usr/bin/env python3
"""The claims checker (spec § The checker and the generator).

Rules: schema (0) · owner (1) · tag (2) · pointer (3) · untagged (4, warning only) · generator (5)
· skill (6) · example (7). --register-only runs 0 and 3; --partial lets 1 skip owner pages that do
not exist yet; --fix-tags rewrites every tag's suffix from the register; --view LAYER and
--section-map print register slices; --staged skips the run when nothing relevant is staged."""
import argparse, collections, csv, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claimslib as cl

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = "docs/reference/claims.tsv"
DNC = "docs/reference/do-not-cite.csv"
ALIASES = "docs/reference/run-aliases.csv"
HARNESS_MD = "docs/reference/harness-commands.md"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
LAYER_DIRS = ("docs/areas", "docs/platform", "docs/facts")
# Rule 2 also reads the two reference pages that own register rows: `docs/reference/` is outside the
# page contract, so rule 4 never runs there, but a row owned by one of these still needs its tag to
# resolve and to carry the canonical suffix. Every other reference page is generated or an index.
REF_TAG_PAGES = ("docs/reference/datasets.md", "docs/reference/tools.md")
SKILLS_DIR = ".claude/skills"
# Trees the Phase 4 cut deletes. A `repo:` pointer into one of them is a dangling cite the moment
# the cut lands, so rule 3 rejects it today, whether or not the file still exists (R20). A trailing
# `/` is a prefix; the three bare files are matched whole.
DOOMED_PATHS = ("docs/vanilla/", "docs/modding/", "docs/mods-survey/", "docs/testing/",
                "docs/superpowers/", "docs/feasibility/",
                "docs/progress.md", "docs/decisions.md", "docs/references.md")
# Exempt: the cut moves this file verbatim to docs/reference/wall-map.md and rewrites the
# register's pointers then, so a pointer into it is not a dangling cite (R21).
DOOMED_EXEMPT = ("docs/modding/wall-map.md",)
TRIGGERS = ("docs/", ".claude/skills/", "testing/PZTestKit/", "testing/artifacts/", "testing/experiments/", "tools/bus_inventory.py")
Finding = collections.namedtuple("Finding", "path line rule detail")
WARN_RULES = ("untagged",)
PROVISIONAL_MSG = "provisional tag %s (apply the delta, or --allow-provisional)"
H2_RX = re.compile(r"^## (.+?)\s*$")
CODE_SPAN_RX = re.compile(r"`[^`]*`")
FILE_LINES_RX = re.compile(r"`?([A-Za-z0-9_./-]+\.[A-Za-z0-9]+):\d+(?:[-–]\d+)?`?")


def is_warning(f):
    return f.rule in WARN_RULES


def exit_code(findings):
    return 1 if any(not is_warning(f) for f in findings) else 0


def _rel(path, root):
    return os.path.relpath(path, root).replace("\\", "/")


def _read(path):
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        return f.read()


def _md_files(root, dirs):
    for d in dirs:
        base = os.path.join(root, *d.split("/"))
        for dp, _, fns in os.walk(base):
            for fn in sorted(fns):
                if fn.endswith(".md"):
                    yield os.path.join(dp, fn)


def _skill_files(root):
    base = os.path.join(root, *SKILLS_DIR.split("/"))
    return sorted(os.path.join(base, d, "SKILL.md") for d in os.listdir(base) if os.path.exists(os.path.join(base, d, "SKILL.md"))) if os.path.isdir(base) else []


def _tagged_files(root):
    """Every file rule 2 checks and --fix-tags rewrites: the three layers, the two reference
    pages that own register rows (when they exist), and the skills."""
    extra = [os.path.join(root, *r.split("/")) for r in REF_TAG_PAGES]
    return list(_md_files(root, LAYER_DIRS)) + [p for p in extra if os.path.exists(p)] + _skill_files(root)


def _sections(text):
    """[(heading or '', [(lineno, line), ...])] split on '## ' headings; fences and tables kept as lines."""
    out, cur, lines = [], ("", []), text.replace("\r\n", "\n").split("\n")
    for n, line in enumerate(lines, 1):
        m = H2_RX.match(line)
        if m:
            out.append(cur); cur = (m.group(1), [])
        else:
            cur[1].append((n, line))
    out.append(cur)
    return out


def _load_csv(path):
    """Every row of a CSV as a dict; [] when the file is absent."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _keyed(rows, key):
    """({value of `key`: row}, how many rows lacked it). A CSV written with the wrong header is a
    finding naming the file, never a KeyError in the middle of a pre-commit gate."""
    return {r[key]: r for r in rows if r.get(key)}, sum(1 for r in rows if not r.get(key))


def _utf8_console():
    """Findings quote page text verbatim; the default Windows console encoding (cp1252) cannot
    encode `≈`, `→`, `−`, `≥` or `≤` and would abort the run, losing every later finding and the
    summary. Same guard as tools/doc_lint.py."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


def _minted_from(n):
    """The name of the block `n` was minted from: the last one whose range starts at or below it,
    or None when `n` is below the first block.

    `cl.block_of` answers "which block *contains* this id" and calls an id past a block's last id
    unblocked, so an overflow would disappear instead of being reported. Rule 0 needs the block the
    id was minted from, which is the same answer whenever `cl.BLOCKS` is contiguous (it is today)
    and the honest one the moment it is not."""
    found = None
    for name, lo, _hi in cl.BLOCKS:
        if n >= lo:
            found = name
    return found


def rule_schema(rows, register_rel):
    out, seen = [], {}
    for n, r in enumerate(rows, 2):
        for e in cl.validate_row(r):
            out.append(Finding(register_rel, n, "schema", "%s: %s" % (r.get("id"), e)))
        if r["id"] in seen:
            out.append(Finding(register_rel, n, "schema", "%s: duplicate id (first at line %d)" % (r["id"], seen[r["id"]])))
        seen.setdefault(r["id"], n)
    ids = {r["id"] for r in rows}
    for r in rows:
        for s in [s.strip() for s in r.get("successor", "").split(",") if s.strip()]:
            if s not in ids:
                out.append(Finding(register_rel, seen.get(r["id"], 1), "schema", "%s: successor %s is not in the register" % (r["id"], s)))
    by_block, stray = collections.defaultdict(set), []
    for r in rows:
        if not cl.ID_FULL_RX.match(r["id"]):
            continue                            # already a rule-0 finding from validate_row
        n = cl.id_int(r["id"])
        b = _minted_from(n)
        if b is None:
            stray.append(n)
        else:
            by_block[b].add(n)
    if stray:
        out.append(Finding(register_rel, 1, "schema", "%s is outside every reserved id block (the first is %s, from %s)"
                           % (cl.id_str(min(stray)), cl.BLOCKS[0][0], cl.id_str(cl.BLOCKS[0][1]))))
    for name, lo, hi in cl.BLOCKS:
        used = by_block.get(name)
        if not used:
            continue
        # The block's upper bound. Without this a harvest part that runs past its reserved
        # sub-block passes --register-only on its own and only collides with its neighbour at
        # the merge; `hi` is otherwise never read.
        # Where the contiguity run is anchored. Normally the block's own first id — but with
        # `--register <part>` a part may hold a *continuation* slice that legitimately starts later
        # (the post block especially), so when the block's `lo` is absent the run is anchored at the
        # slice's own first id and only its internal contiguity is required (R22). The merged
        # register always holds `lo` for any block it uses, so the full rule applies at the merge.
        first = lo if lo in used else min(used)
        over = sorted(n for n in used if n > hi)
        if over:
            out.append(Finding(register_rel, 1, "schema", "block %s: id %s is past the block's last id %s"
                               % (name, cl.id_str(over[0]), cl.id_str(hi))))
        elif first + len(used) - 1 > hi:
            out.append(Finding(register_rel, 1, "schema", "block %s: %d ids do not fit between %s and %s; %s is past its last id"
                               % (name, len(used), cl.id_str(first), cl.id_str(hi), cl.id_str(hi + 1))))
        else:
            expected = set(range(first, first + len(used)))
            if used != expected:
                missing = sorted(expected - used)[:5]
                out.append(Finding(register_rel, 1, "schema", "block %s: ids are not contiguous from %s (gap at %s)"
                                   % (name, cl.id_str(first), ", ".join(cl.id_str(m) for m in missing))))
    return out


def _doomed(path):
    """True for a repo path under a tree the Phase 4 cut deletes (R20), bar the files the cut moves
    rather than deletes (R21) — those still go through the ordinary "does it exist" check."""
    if path in DOOMED_EXEMPT:
        return False
    return any(path.startswith(d) if d.endswith("/") else path == d for d in DOOMED_PATHS)


def _uncommitted_run(row):
    """The spec's form for an M claim whose only run left no artifact: `status unverified` — or
    `superseded`, which keeps the old evidence as the source wrote it — with a bound that starts
    `uncommitted: <run-id>`. Rule 3 admits a missing run folder only on such a row (R17, widened by
    R20) — the row keeps the source's grade and pointer, and its owner lists it under `## Open` with
    the re-measurement that settles it. A settled or open row citing a run with no folder is still a
    finding, and so is an unverified or superseded row bounded any other way."""
    if row.get("status") not in ("unverified", "superseded"):
        return False
    try:
        token, _ = cl.parse_bound(row.get("bound", ""))
    except ValueError:
        return False                                # already a rule-0 finding from validate_row
    return token == "uncommitted"


def _restricted_key(key, listed):
    """The do-not-cite key that restricts `key`, or None (Ruling R34).

    A cited key is uncitable when it *equals* a listed key for that run, or when it is a **child**
    of one — `<listed>.<rest>` or `<listed>[<index>` — because the restriction on a reading covers
    every reading inside it. An **ancestor** of a listed key is not flagged here (a parent object
    may hold citable siblings; narrowing that is a Phase 2 checker item). A `*` row is a whole-run
    prose restriction, not a key path: it still only matches by equality, so it never fails a row
    on its own and goes on being discharged by quoting its `why` into the row's bound. The most
    specific listed key wins, so the finding names the closest restriction."""
    if key in listed:
        return key
    hits = [k for k in listed if k and k != "*" and (key.startswith(k + ".") or key.startswith(k + "["))]
    return min(hits, key=lambda k: (-len(k), k)) if hits else None


def rule_pointer(rows, root, register_rel):
    out = []
    # do-not-cite.csv is `run,key,value,why,read_instead`; a prose restriction with no key has
    # `key = *`. Keyed by run, because the test is no longer an exact `(run, key)` tuple: see
    # _restricted_key for the child-key rule (R34).
    dnc = collections.defaultdict(set)
    for dr in _load_csv(os.path.join(root, DNC)):
        dnc[dr.get("run", "")].add(dr.get("key", ""))
    aliases, unkeyed = _keyed(_load_csv(os.path.join(root, ALIASES)), "alias")
    if unkeyed:
        out.append(Finding(ALIASES, 1, "pointer", "%d row(s) in run-aliases.csv carry no 'alias' column and are "
                                                  "ignored; the columns are alias,run,file,key" % unkeyed))
    for n, r in enumerate(rows, 2):
        try:
            ptrs = cl.parse_pointers(r["pointer"])
        except ValueError:
            continue    # rule 0 already reported it
        for form, text in ptrs:
            if form == "run":
                parts = text.split()
                run = parts[0] if parts else ""
                real = aliases[run]["run"] if run in aliases else run
                rdir = os.path.join(root, "testing", "artifacts", real)
                if not os.path.isdir(rdir):
                    if not _uncommitted_run(r):
                        out.append(Finding(register_rel, n, "pointer", "%s: run %s has no folder under testing/artifacts/ (no alias either)" % (r["id"], run)))
                    continue
                if len(parts) >= 2 and parts[1].endswith(".json") and not os.path.exists(os.path.join(rdir, parts[1])):
                    out.append(Finding(register_rel, n, "pointer", "%s: %s has no file %s" % (r["id"], real, parts[1])))
                key = " ".join(parts[2:]) if len(parts) >= 3 else ""
                listed = _restricted_key(key, dnc[real]) or _restricted_key(key, dnc[run])
                if listed:
                    detail = "%s: %s %s is on the do-not-cite list" % (r["id"], real, key)
                    if listed != key:
                        detail += " (a child of the restricted key %s)" % listed
                    out.append(Finding(register_rel, n, "pointer", detail))
            elif form == "repo":
                path = text.split('"')[0].strip().rsplit(":", 1)[0]
                if _doomed(path):
                    out.append(Finding(register_rel, n, "pointer", "%s: repo path %s is deleted at the cut (Phase 4); "
                                                                   "cite the underlying evidence" % (r["id"], path)))
                elif not os.path.exists(os.path.join(root, *path.split("/"))):
                    out.append(Finding(register_rel, n, "pointer", "%s: repo path %s does not exist" % (r["id"], path)))
    return out


def rule_owner(rows, root, partial):
    out = []
    for r in rows:
        if r["status"] == "superseded" or not cl.OWNER_RX.match(r["owner"]):
            continue
        page = r["owner"].split("#")[0]
        path = os.path.join(root, "docs", *page.split("/"))
        if not os.path.exists(path):
            if not partial:
                out.append(Finding("docs/" + page, 1, "owner", "%s: owner page does not exist" % r["id"]))
            continue
        if r["id"] not in {cid for _, cid, _ in cl.iter_tags(_read(path))}:
            out.append(Finding("docs/" + page, 1, "owner", "%s: owner page carries no tag for it" % r["id"]))
    return out


def rule_tag(rows, root, allow_provisional):
    out, by_id = [], {r["id"]: r for r in rows}
    for path in _tagged_files(root):
        rel, text = _rel(path, root), _read(path)
        prov = set()
        for n, cid, suffix in cl.iter_tags(text):
            if cl.is_provisional(cid):
                # A `T<task>.<n>` item inside a mixed bracket is a marker, not a register id:
                # it is a provisional finding, never "not in the register", and block_of /
                # id_int are never called on it.
                prov.add((n, cid))
            elif cid not in by_id:
                out.append(Finding(rel, n, "tag", "%s is not in the register" % cid))
            else:
                want = cl.canonical_suffix(by_id[cid])
                if suffix != want:
                    out.append(Finding(rel, n, "tag", "%s: suffix %r should be %r (run --fix-tags)" % (cid, suffix, want)))
        if not allow_provisional:
            # A lone `[T3.7]` is not a tag, so iter_tags never sees it; find_provisional reads
            # every bracket shape. The set keeps a mixed bracket to one finding.
            for n, line in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
                prov.update((n, pid) for pid in cl.find_provisional(line))
            for n, pid in sorted(prov):
                out.append(Finding(rel, n, "tag", PROVISIONAL_MSG % pid))
    return out


def rule_untagged(root):
    out = []
    for path in _md_files(root, LAYER_DIRS):     # never under docs/reference/ (spec § Open questions 4)
        rel, fence = _rel(path, root), False
        for heading, lines in _sections(_read(path)):
            if heading.startswith("Procedure"):
                continue
            for n, line in lines:
                if line.startswith("```"):
                    fence = not fence; continue
                if fence or line.startswith("|") or line.startswith("#") or line.startswith("Verified against") or not line.strip():
                    continue
                bare = CODE_SPAN_RX.sub("", line)
                if re.search(r"\d", bare) and not cl.TAG_RX.search(line) and not cl.PROVISIONAL_RX.search(line):
                    out.append(Finding(rel, n, "untagged", "a number without a tag: %s" % line.strip()[:70]))
    return out


def rule_generator(root, lua_dir):
    import bus_inventory as bi
    md = os.path.join(root, *HARNESS_MD.split("/"))
    if not os.path.isdir(lua_dir):
        return []
    if not os.path.exists(md):
        return [Finding(HARNESS_MD, 1, "generator", "missing; run python tools/bus_inventory.py")]
    sites = bi.scan(lua_dir)
    if any(s["missing"] for s in sites):
        return [Finding(HARNESS_MD, 1, "generator", "%d TK.register sites lack a complete comment block" % sum(1 for s in sites if s["missing"]))]
    # The header's directory label is made in exactly one place, so this rule and the generator's
    # own --check can never disagree about it on a clean checkout.
    if _read(md).replace("\r\n", "\n") != bi.render(sites, bi.label_for(lua_dir, root=root)):
        return [Finding(HARNESS_MD, 1, "generator", "drift: not a fresh render; run python tools/bus_inventory.py")]
    return []


def _bullets(sections, heading):
    for h, lines in sections:
        if h.strip().lower() == heading:
            return [(n, l[2:].strip()) for n, l in lines if l.startswith("- ")]
    return []


def rule_skill(root):
    out = []
    for path in _skill_files(root):
        rel, secs = _rel(path, root), _sections(_read(path))
        pages = [m.group(1) for _, l in _bullets(secs, "read first") for m in [re.search(r"(docs/[A-Za-z0-9_./-]+\.md)", l)] if m]
        rules = set()
        for page in pages:
            p = os.path.join(root, *page.split("/"))
            if os.path.exists(p):
                rules |= {l for _, l in _bullets(_sections(_read(p)), "rules")}
        for n, quoted in _bullets(secs, "rules quoted"):
            if quoted not in rules:
                out.append(Finding(rel, n, "skill", "quoted rule is not verbatim on a Read-first page: %s" % quoted[:70]))
    return out


def rule_example(root):
    out = []
    # Every layer: the page contract puts `## Worked examples` on platform/ pages with code shapes
    # and calls it "optional elsewhere", so an areas/ or facts/ page may carry one too.
    for path in _md_files(root, LAYER_DIRS):
        rel = _rel(path, root)
        for heading, lines in _sections(_read(path)):
            if not heading.startswith("Worked examples"):
                continue
            for n, line in lines:
                if line.startswith("|") and not re.match(r"^\|\s*:?-", line):
                    cells = [c.strip() for c in line.strip("|").split("|")]
                    if len(cells) >= 2 and cells[0].lower() != "shape":
                        m = FILE_LINES_RX.search(cells[1])
                        if not m or not os.path.exists(os.path.join(root, *m.group(1).split("/"))):
                            out.append(Finding(rel, n, "example", "worked example path does not exist: %s" % cells[1]))
    return out


def fix_tags(root, register=None, rows=None):
    rows = cl.read_register(register or os.path.join(root, *REGISTER.split("/"))) if rows is None else rows
    by_id = {r["id"]: r for r in rows}
    changed = 0
    for path in _tagged_files(root):     # the same files rule 2 checks, or it would report drift --fix-tags cannot fix
        text = _read(path)

        def fix(m):
            # A provisional item keeps its own text: it is not in the register and never will be
            # until the controller applies the delta.
            items = ["%s%s" % (cid, cl.canonical_suffix(by_id[cid]) if cid in by_id else suffix) for cid, suffix in cl.split_tag(m.group(1))]
            return "[" + ", ".join(items) + "]"

        new = cl.TAG_RX.sub(fix, text)
        if new != text:
            open(path, "w", encoding="utf-8", newline="").write(new); changed += 1
    return changed


def section_map(rows):
    out = collections.defaultdict(list)
    for r in rows:
        for src in [s.strip() for s in r["source"].split(";") if s.strip()]:
            out[src].append(r["id"])
    return dict(out)


def staged_paths(root):
    """The staged paths, or None when git could not answer. None is not "nothing staged": a git
    failure must make --staged run the full check, never silently skip the gate."""
    try:
        r = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=root, capture_output=True, text=True)
    except OSError:
        return None
    if r.returncode != 0:
        return None
    return [p.strip() for p in r.stdout.splitlines() if p.strip()]


def _read_rows(root, register):
    """(rows, None), or (None, the one `schema` finding a bad register produces)."""
    path = register or os.path.join(root, *REGISTER.split("/"))
    try:
        return cl.read_register(path), None
    except (cl.RegisterError, OSError) as e:
        return None, Finding(_rel(path, root), 1, "schema", str(e))


def check(root=None, register=None, lua_dir=None, register_only=False, partial=False, allow_provisional=False):
    root = root or REPO_ROOT
    reg_rel = _rel(register or os.path.join(root, *REGISTER.split("/")), root)
    rows, err = _read_rows(root, register)
    if err is not None:
        return [err]
    findings = rule_schema(rows, reg_rel) + rule_pointer(rows, root, reg_rel)
    if register_only:
        return findings
    lua = lua_dir or os.path.join(root, *LUA_DIR.split("/"))
    findings += rule_owner(rows, root, partial) + rule_tag(rows, root, allow_provisional) + rule_untagged(root)
    findings += rule_generator(root, lua) + rule_skill(root) + rule_example(root)
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=REPO_ROOT); ap.add_argument("--register"); ap.add_argument("--lua-dir")
    ap.add_argument("--register-only", action="store_true"); ap.add_argument("--partial", action="store_true")
    ap.add_argument("--staged", action="store_true"); ap.add_argument("--allow-provisional", action="store_true")
    ap.add_argument("--fix-tags", action="store_true"); ap.add_argument("--view"); ap.add_argument("--section-map", action="store_true")
    a = ap.parse_args(argv)
    _utf8_console()
    root = os.path.abspath(a.root)
    if a.staged:
        staged = staged_paths(root)
        if staged is None:
            print("git could not list the staged paths; checking everything")
        elif not any(p.startswith(TRIGGERS) for p in staged):
            print("nothing staged under the checker's trigger paths; skipped"); return 0
    if a.fix_tags or a.view or a.section_map:
        rows, err = _read_rows(root, a.register)
        if err is not None:
            return _report([err])                      # a bad register is a finding, not a traceback
        if a.fix_tags:
            print("%d files rewritten" % fix_tags(root, rows=rows))
        if a.view:
            for r in rows:
                if r["owner"].startswith(a.view.rstrip("/") + "/"):
                    print("\t".join(r[c] for c in cl.COLUMNS))
        if a.section_map:
            for src, ids in sorted(section_map(rows).items()):
                print("%s -> %s" % (src, ", ".join(ids)))
        if a.view or a.section_map:
            return 0
    return _report(check(root, a.register, a.lua_dir, a.register_only, a.partial, a.allow_provisional))


def _report(findings):
    for f in sorted(findings, key=lambda f: (f.path, f.line, f.rule)):
        print("%s:%d: %s: %s%s" % (f.path, f.line, f.rule, f.detail, " (warning)" if is_warning(f) else ""))
    n_err = sum(1 for f in findings if not is_warning(f)); n_warn = len(findings) - n_err
    print("%d findings, %d warnings" % (n_err, n_warn))
    return exit_code(findings)


if __name__ == "__main__":
    sys.exit(main())
