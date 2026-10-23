#!/usr/bin/env python3
"""The claims checker (spec § The checker and the generator).

Rules: schema (0) · owner (1) · tag (2) · pointer (3; 3b `pointer-line`: a `repo:` pointer's quoted text must be on its cited line or range; `repo:<path>@<commit>:<line> "<quote>"` pins a commit and is read through `git show`, for code since removed) · untagged (4, warning only; a digit inside a
markdown link target is not a number) · generator (5) · skill (6) · example (7) · fix-tags and views
(8: --fix-tags writes each tag's suffix from the register; --view LAYER|LAYER/PAGE.md prints a
register slice) · rules-dup (9: for each pair of pages under docs/areas and docs/platform and each
tag-id set both carry on a `## Rules` line, a finding fires only when the two pages share no
byte-identical line for that set; a page's several rules on one set are never compared with each
other) · refgen (10: the two generated sections must be fresh renders of the register —
docs/reference/artifacts.md's `Cited by` column and the `## Contradictions` section of
references/wiki-mirrors/README.md; an absent page or a README without its reference_gen markers is a
finding; see tools/reference_gen.py). --register-only runs 0 and 3; --partial lets
1 skip owner pages that do not exist yet; --section-map prints the source-section map; --staged
skips the run when nothing relevant is staged."""
import argparse, collections, csv, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claimslib as cl

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = "docs/reference/claims.tsv"
# The archive register: the same columns, one id space with the live file (ruling P20-T1-1). It holds only
# superseded and retired rows (P20-T1-2); an absent archive is an empty one.
ARCHIVE = "docs/reference/claims-archive.tsv"
DNC = "docs/reference/do-not-cite.csv"
ALIASES = "docs/reference/run-aliases.csv"
HARNESS_MD = "docs/reference/harness-commands.md"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
LAYER_DIRS = ("docs/areas", "docs/platform", "docs/facts")
# Rule 2 also reads the three reference pages that own register rows: `docs/reference/` is outside the
# page contract, so rule 4 never runs there, but a row owned by one of these still needs its tag to
# resolve and to carry the canonical suffix. Every other reference page is generated or an index.
REF_TAG_PAGES = ("docs/reference/datasets.md", "docs/reference/tools.md", "docs/reference/wall-map.md")
# Rule 10's inputs: the two files whose sections tools/reference_gen.py generates.
ARTIFACTS_MD = "docs/reference/artifacts.md"
MIRRORS_README = "references/wiki-mirrors/README.md"
SKILLS_DIR = ".claude/skills"
# The pre-restructure trees, readable only at the tag research-program-v1. A `repo:` pointer into one
# of them is a dangling cite, so rule 3 rejects it whether or not a stray file sits at that path (R20).
# A trailing `/` is a prefix; the three bare files are matched whole.
DOOMED_PATHS = ("docs/vanilla/", "docs/modding/", "docs/mods-survey/", "docs/testing/",
                "docs/superpowers/", "docs/feasibility/",
                "docs/progress.md", "docs/decisions.md", "docs/references.md")
# The one doomed tree a pinned pointer may still name: the program record, archived at a tag (Plan 20).
PINNABLE_PATHS = ("docs/superpowers/",)
TRIGGERS = ("docs/", ".claude/skills/", "testing/PZTestKit/", "testing/artifacts/", "testing/experiments/", "tools/bus_inventory.py", "tools/reference_gen.py", "references/wiki-mirrors/")
Finding = collections.namedtuple("Finding", "path line rule detail")
WARN_RULES = ("untagged",)
PROVISIONAL_MSG = "provisional tag %s (apply the delta, or --allow-provisional)"
H2_RX = re.compile(r"^## (.+?)\s*$")
CODE_SPAN_RX = re.compile(r"`[^`]*`")
LINK_TARGET_RX = re.compile(r"\]\([^)\s]*\)")
ANCHOR_LINE_RX = re.compile(r'^\s*<a id="[A-Za-z0-9_-]+"></a>\s*$')
RULES_DIRS = ("docs/areas", "docs/platform")
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
    """Every file rule 2 checks and --fix-tags rewrites: the three layers, the three reference
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


def rule_schema(rows, register_rel, archive=(), archive_rel=ARCHIVE):
    """Rule 0 over the live register and its archive as one id space (P20-T1-1): each row's schema, a duplicate id in
    either file or across the two, a successor in neither, and the id blocks' contiguity over the union. A row in the
    archive is superseded or retired, and a retired row lives only there (P20-T1-2); a superseded row's successor is
    never an archived retired row (P20-T1-3)."""
    out, seen = [], {}
    entries = [(register_rel, n, r, False) for n, r in enumerate(rows, 2)]
    entries += [(archive_rel, n, r, True) for n, r in enumerate(archive, 2)]
    for rel, n, r, archived in entries:
        for e in cl.validate_row(r):
            out.append(Finding(rel, n, "schema", "%s: %s" % (r.get("id"), e)))
        if r["id"] in seen:
            frel, fn = seen[r["id"]]
            where = "line %d" % fn if frel == rel else "%s:%d" % (frel, fn)
            out.append(Finding(rel, n, "schema", "%s: duplicate id (first at %s)" % (r["id"], where)))
        seen.setdefault(r["id"], (rel, n))
        if archived and r.get("status") not in cl.ARCHIVE_STATUSES:
            out.append(Finding(rel, n, "schema", "%s: an archived row with status %s; the archive holds only %s rows"
                               % (r["id"], r.get("status"), " and ".join(cl.ARCHIVE_STATUSES))))
        if not archived and r.get("status") == "retired":
            out.append(Finding(rel, n, "schema", "%s: a retired row in the live register; claims_delta.py's retire op "
                                                 "moves it to %s" % (r["id"], archive_rel)))
    status = {}
    for _, _, r, archived in entries:
        status.setdefault(r["id"], (r.get("status"), archived))
    for rel, n, r, _ in entries:
        for s in [s.strip() for s in r.get("successor", "").split(",") if s.strip()]:
            if s not in status:
                out.append(Finding(rel, n, "schema", "%s: successor %s is not in the register or its archive" % (r["id"], s)))
            elif status[s] == ("retired", True):
                out.append(Finding(rel, n, "schema", "%s: successor %s is a retired row; a superseded row's successor is never retired"
                                   % (r["id"], s)))
    rows = [r for _, _, r, _ in entries]
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


def _doomed(path, pinned=False):
    """True for a repo path under a pre-restructure tree (R20); any other path goes through the
    ordinary "does it exist" check. A pinned path under one of PINNABLE_PATHS is not doomed: the program
    record is cited at its tag (`repo:docs/superpowers/<file>@program-record-v19:<line>`, Plan 20)."""
    if pinned and any(path.startswith(d) for d in PINNABLE_PATHS):
        return False
    return any(path.startswith(d) if d.endswith("/") else path == d for d in DOOMED_PATHS)


def _uncommitted_run(row):
    """The spec's form for an M claim whose only run left no artifact: `status unverified` — or
    `superseded`, which keeps the old evidence as the source wrote it — with a bound that starts
    `uncommitted: <run-id>`. Rule 3 admits a missing run folder only on such a row (R17, widened by
    R20) — the row keeps the source's grade and pointer, and its owner lists it under `## Open` with
    the re-measurement that settles it. A settled or open row citing a run with no folder is still a
    finding, and so is an unverified or superseded row bounded any other way."""
    if row.get("status") not in ("unverified", "superseded", "retired"):
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


REPO_LINE_RX = re.compile(r'^(\S+?):(\d+)(?:-(\d+))?\s+"(.*)"\s*$')
_SHOW_CACHE = {}
_REF_CACHE = {}


def _split_pin(path):
    """'mod/x.lua@abc1234' -> ('mod/x.lua', 'abc1234'), a tag name likewise; an unpinned path -> (path, None)."""
    return cl.split_pin(path)


def _rev_parse(root, spec):
    try:
        p = subprocess.run(["git", "-C", root, "rev-parse", "--verify", "--quiet", spec], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout.decode("ascii", errors="replace").strip() if p.returncode == 0 else None


def _ref_problem(root, ref):
    """None when the pin `ref` names a commit (7 to 40 hex digits) or a tag that git resolves in `root`; else the
    finding's text. A branch or a symbolic ref (HEAD) is refused: it moves, so it pins nothing (P20-T1-6)."""
    key = (root, ref)
    if key not in _REF_CACHE:
        if cl.HEX_REF_RX.match(ref):
            ok = _rev_parse(root, ref + "^{commit}")
            _REF_CACHE[key] = None if ok else "does not resolve at commit %s (unknown commit or no such path there)" % ref
        elif _rev_parse(root, "refs/tags/%s^{commit}" % ref):
            _REF_CACHE[key] = None
        elif _rev_parse(root, ref + "^{commit}"):
            _REF_CACHE[key] = "is pinned at %s, a branch or a symbolic ref, not a tag or a commit; pin a tag or a sha" % ref
        else:
            _REF_CACHE[key] = "does not resolve at tag %s (no such tag)" % ref
    return _REF_CACHE[key]


def _git_show(root, commit, path):
    """The text of `path` at `commit` through `git show`, or None when the commit or the path does not
    resolve. Read-only; cached per (root, commit, path) so each pinned pointer costs one call."""
    key = (root, commit, path)
    if key not in _SHOW_CACHE:
        try:
            p = subprocess.run(["git", "-C", root, "show", "%s:%s" % (commit, path)], capture_output=True, timeout=60)
            _SHOW_CACHE[key] = p.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n") if p.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            _SHOW_CACHE[key] = None
    return _SHOW_CACHE[key]


def _pointer_line_finding(r, text, n, root, register_rel):
    """Rule 3b: a `repo:<path>:<line>[-<line>] "<text>"` pointer's quoted text must occur on that line
    (or inside that range) of the working-tree file. A path under testing/artifacts/ and a line-less
    pointer are exempt; a superseded row is checked like any other (its stale quote is pinned to the last
    commit holding it), and so is every pointer of a multi-pointer cell; a missing file is rule 3's
    finding, not this one's."""
    m = REPO_LINE_RX.match(text.strip())
    if not m or m.group(1).startswith("testing/artifacts/"):
        return None
    path, lo, hi, quoted = m.group(1), int(m.group(2)), int(m.group(3) or m.group(2)), m.group(4)
    path, commit = _split_pin(path)
    if commit:
        body = None if _ref_problem(root, commit) else _git_show(root, commit, path)
        if _doomed(path, pinned=True) or body is None:
            return None    # rule 3 reports an unresolvable pin
        lines = body.split("\n")
    else:
        full = os.path.join(root, *path.split("/"))
        if _doomed(path) or not os.path.isfile(full):
            return None
        with open(full, encoding="utf-8", errors="replace", newline="") as fh:
            lines = fh.read().replace("\r\n", "\n").split("\n")
    if quoted in "\n".join(lines[lo - 1:hi]):
        return None
    hits = [i for i, ln in enumerate(lines, 1) if quoted in ln]
    where = "found at %d" % min(hits, key=lambda i: abs(i - lo)) if hits else "not found"
    cited = "%d-%d" % (lo, hi) if hi != lo else "%d" % lo
    shown = "%s@%s" % (path, commit) if commit else path
    return Finding(register_rel, n, "pointer-line", '#%s repo:%s:%s — "%s" not on that line (%s)' % (r["id"].lstrip("#"), shown, cited, quoted, where))


def rule_pointer(rows, root, register_rel, archived=False):
    """Rule 3 over the live register, or (archived=True) over the archive: there a superseded row's pointers are never
    resolved, and a retired row's are resolved like a live row's, every `repo:` pointer pinned (P20-T1-3)."""
    out = []
    # do-not-cite.csv is `run,key,value,why,read_instead`; a prose restriction with no key has
    # `key = *`. Keyed by run, because the test is no longer an exact `(run, key)` tuple: see
    # _restricted_key for the child-key rule (R34).
    dnc = collections.defaultdict(set)
    for dr in _load_csv(os.path.join(root, DNC)):
        dnc[dr.get("run", "")].add(dr.get("key", ""))
    aliases, unkeyed = _keyed(_load_csv(os.path.join(root, ALIASES)), "alias")
    if unkeyed and not archived:
        out.append(Finding(ALIASES, 1, "pointer", "%d row(s) in run-aliases.csv carry no 'alias' column and are "
                                                  "ignored; the columns are alias,run,file,key" % unkeyed))
    for n, r in enumerate(rows, 2):
        if archived and r.get("status") != "retired":
            continue    # an archived superseded row keeps its old evidence as written; a stray status is rule 0's
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
                path, commit = _split_pin(path)
                if archived and not commit:
                    out.append(Finding(register_rel, n, "pointer", "%s: a retired row's repo: pointer must be pinned "
                                                                   "(repo:<path>@<commit or tag>:<line>): %s" % (r["id"], path)))
                elif commit:
                    problem = _ref_problem(root, commit)
                    kind = "commit" if cl.HEX_REF_RX.match(commit) else "tag"
                    if _doomed(path, pinned=True):
                        out.append(Finding(register_rel, n, "pointer", "%s: repo path %s is a pre-restructure path (at the tag "
                                                                       "research-program-v1); cite the underlying evidence" % (r["id"], path)))
                    elif problem:
                        out.append(Finding(register_rel, n, "pointer", "%s: repo path %s %s" % (r["id"], path, problem)))
                    elif _git_show(root, commit, path) is None:
                        out.append(Finding(register_rel, n, "pointer", "%s: repo path %s does not resolve at %s %s (no such path there)" % (r["id"], path, kind, commit)))
                    else:
                        f = _pointer_line_finding(r, text, n, root, register_rel)
                        if f:
                            out.append(f)
                elif _doomed(path):
                    out.append(Finding(register_rel, n, "pointer", "%s: repo path %s is a pre-restructure path (at the tag "
                                                                   "research-program-v1); cite the underlying evidence" % (r["id"], path)))
                elif not os.path.exists(os.path.join(root, *path.split("/"))):
                    out.append(Finding(register_rel, n, "pointer", "%s: repo path %s does not exist" % (r["id"], path)))
                else:
                    f = _pointer_line_finding(r, text, n, root, register_rel)
                    if f:
                        out.append(f)
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


def rule_tag(rows, root, allow_provisional, archive=()):
    """Rule 2: every tag names a live register row with its canonical suffix. A tag naming an archived row is a
    finding: an archived row is cited from the archive, never from a page (Plan 20)."""
    out, by_id = [], {r["id"]: r for r in rows}
    archived = {r["id"]: r for r in archive}
    for path in _tagged_files(root):
        rel, text = _rel(path, root), _read(path)
        prov = set()
        for n, cid, suffix in cl.iter_tags(text):
            if cl.is_provisional(cid):
                # A `T<task>.<n>` item inside a mixed bracket is a marker, not a register id:
                # it is a provisional finding, never "not in the register", and block_of /
                # id_int are never called on it.
                prov.add((n, cid))
            elif cid not in by_id and cid in archived:
                a = archived[cid]
                succ = " (its successor: %s)" % a["successor"] if a.get("successor", "").strip() else ""
                out.append(Finding(rel, n, "tag", "%s is archived (%s in %s); a page never tags an archived row%s"
                                   % (cid, a.get("status"), ARCHIVE, succ)))
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
                if ANCHOR_LINE_RX.match(line):     # a bare <a id="x13"></a> line: the slug is a name, never a number
                    continue
                bare = LINK_TARGET_RX.sub("]", CODE_SPAN_RX.sub("", line))     # the link text stays; its target goes
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


def rule_refgen(root, rows):
    """Rule 10: each generated section of the reference is a fresh render of the register (spec
    § The target tree): the artifacts register's `Cited by` column in docs/reference/artifacts.md
    and the wiki mirrors' `## Contradictions` section in references/wiki-mirrors/README.md. Both
    inputs are mandatory: an absent file is a finding, and so is a README without its markers
    (`contradictions_check` reports the missing section)."""
    import reference_gen as rg
    out = []
    page = os.path.join(root, *ARTIFACTS_MD.split("/"))
    if not os.path.exists(page):
        out.append(Finding(ARTIFACTS_MD, 1, "refgen", "missing: the artifacts register does not exist, "
                                                      "so its Cited by column cannot be checked"))
    else:
        for d in rg.cited_by_check(page, rows, os.path.join(root, *ALIASES.split("/"))):
            out.append(Finding(ARTIFACTS_MD, 1, "refgen", d))
    readme = os.path.join(root, *MIRRORS_README.split("/"))
    if not os.path.exists(readme):
        out.append(Finding(MIRRORS_README, 1, "refgen", "missing: the wiki mirrors README does not exist, "
                                                        "so its Contradictions section cannot be checked"))
    else:
        for d in rg.contradictions_check(readme, rows):
            out.append(Finding(MIRRORS_README, 1, "refgen", d))
    return out


def rule_guide(root, rows, archive=(), register_rel=REGISTER, archive_rel=ARCHIVE):
    """Rule 11: the runs' reading guides (P20-T1-7). A guide is inline on docs/reference/artifacts.md or its own file
    testing/artifacts/<run>/GUIDE.md, linked from the run's Contents row; both forms are read. A link that names
    another path or a missing file is a finding, and so is a run that keeps both forms. The wildcard sentence (CLAUDE.md
    section 4, items 9 and 11): a `run:` pointer of a live row or an archived retired row whose key a wildcard in that
    run's guide restricts is a finding, read from whichever form the run's guide takes."""
    import reference_gen as rg
    page = os.path.join(root, *ARTIFACTS_MD.split("/"))
    if not os.path.exists(page):
        return []                                   # rule 10 reports the missing page
    text = _read(page)
    try:
        links = rg.guide_links(text)
    except ValueError:
        return []                                   # rule 10 reports the missing Contents table
    out = []
    inline = rg.inline_guides(text)
    for run, target in sorted(links.items()):
        want = "testing/artifacts/%s/%s" % (run, rg.GUIDE_NAME)
        got = rg.guide_rel(target)
        if got != want:
            out.append(Finding(ARTIFACTS_MD, 1, "guide", "%s: the guide link %s names %s; a run's guide is %s"
                               % (run, target, got, want)))
        elif not os.path.isfile(os.path.join(root, *want.split("/"))):
            out.append(Finding(ARTIFACTS_MD, 1, "guide", "%s: the linked guide %s does not exist" % (run, want)))
        if run in inline:
            out.append(Finding(ARTIFACTS_MD, inline[run][0][0], "guide", "%s: the guide is linked (%s) and also inline "
                                                                       "here; a run keeps one guide" % (run, want)))
    aliases, _ = _keyed(_load_csv(os.path.join(root, ALIASES)), "alias")
    cache = {}

    def wild(run):
        if run not in cache:
            src, body = rg.run_guide(root, run, text, links=links, inline=inline)
            cache[run] = (src, rg.wildcard_keys(body))
        return cache[run]

    entries = [(register_rel, n, r) for n, r in enumerate(rows, 2)]
    entries += [(archive_rel, n, r) for n, r in enumerate(archive, 2) if r.get("status") == "retired"]
    for rel, n, r in entries:
        try:
            ptrs = cl.parse_pointers(r["pointer"])
        except ValueError:
            continue                                # rule 0 already reported it
        for form, payload in ptrs:
            parts = payload.split()
            if form != "run" or len(parts) < 3:
                continue
            key = " ".join(parts[2:])
            for run in dict.fromkeys([parts[0], aliases[parts[0]]["run"] if parts[0] in aliases else parts[0]]):
                src, pats = wild(run)
                hit = next((p for p in pats if rg.wildcard_match(p, key)), None)
                if hit:
                    out.append(Finding(rel, n, "guide", "%s: %s %s is restricted by the wildcard %s in its reading guide "
                                                        "(%s)" % (r["id"], run, key, hit, src)))
                    break
    return out


def _bullets(sections, heading):
    for h, lines in sections:
        if h.strip().lower() == heading:
            return [(n, l[2:].strip()) for n, l in lines if l.startswith("- ")]
    return []


def rule_rules_dup(root):
    """Spec § The page contract: a rule that belongs to two areas appears on both pages only as the
    byte-identical line with the same tags; the checker diffs them (Ruling R14). For each pair of
    pages under docs/areas and docs/platform, and each tag-id set both pages carry on a `## Rules`
    line, a finding fires only when the two pages share no byte-identical line for that set: one
    finding per page, on its first line of that set, naming the other page's first line. A page's
    several distinct rules on one set are never compared with each other, and a verbatim copy of one
    rule is clean beside the other rules its source page carries on the same set."""
    pages = {}
    for path in _md_files(root, RULES_DIRS):
        by_ids = {}
        for n, line in _bullets(_sections(_read(path)), "rules"):
            ids = tuple(sorted({cid for _, cid, _ in cl.iter_tags(line)}))
            if ids:
                by_ids.setdefault(ids, []).append((n, line))
        if by_ids:
            pages[_rel(path, root)] = by_ids
    out, rels = [], sorted(pages)
    for i, a in enumerate(rels):
        for b in rels[i + 1:]:
            for ids in sorted(set(pages[a]) & set(pages[b])):
                la, lb = pages[a][ids], pages[b][ids]
                if {t for _, t in la} & {t for _, t in lb}:
                    continue
                tags = " ".join(ids)
                out.append(Finding(a, la[0][0], "rules-dup", "a rule with tags %s has no byte-identical line on %s:%d" % (tags, b, lb[0][0])))
                out.append(Finding(b, lb[0][0], "rules-dup", "a rule with tags %s has no byte-identical line on %s:%d" % (tags, a, la[0][0])))
    return out


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


def _archive_path(root, register, archive):
    """The archive to read beside the register: the one named, else the tree's own when the register is the tree's
    own (a `--register <part>` slice is checked alone), else None."""
    if archive:
        return archive
    return None if register else os.path.join(root, *ARCHIVE.split("/"))


def _read_archive(root, register, archive):
    """(archive rows, None) or (None, its schema finding). The tree's own archive may be absent (an empty archive); one
    named with --archive must exist."""
    path = _archive_path(root, register, archive)
    if path is None or (not archive and not os.path.exists(path)):
        return [], None
    return _read_rows(root, path)


def check(root=None, register=None, lua_dir=None, register_only=False, partial=False, allow_provisional=False, archive=None):
    root = root or REPO_ROOT
    reg_rel = _rel(register or os.path.join(root, *REGISTER.split("/")), root)
    rows, err = _read_rows(root, register)
    if err is not None:
        return [err]
    arch, err = _read_archive(root, register, archive)
    if err is not None:
        return [err]
    arch_rel = _rel(_archive_path(root, register, archive), root) if arch else ARCHIVE
    findings = rule_schema(rows, reg_rel, arch, arch_rel) + rule_pointer(rows, root, reg_rel)
    findings += rule_pointer(arch, root, arch_rel, archived=True)
    if register_only:
        return findings
    lua = lua_dir or os.path.join(root, *LUA_DIR.split("/"))
    findings += rule_owner(rows, root, partial) + rule_tag(rows, root, allow_provisional, arch) + rule_untagged(root)
    findings += rule_generator(root, lua) + rule_refgen(root, rows + arch) + rule_guide(root, rows, arch, reg_rel, arch_rel)
    findings += rule_skill(root) + rule_example(root) + rule_rules_dup(root)
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=REPO_ROOT); ap.add_argument("--register"); ap.add_argument("--archive"); ap.add_argument("--lua-dir")
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
            v = a.view.rstrip("/")
            prefix = v + "#" if v.endswith(".md") else v + "/"
            for r in rows:
                if r["owner"].startswith(prefix):
                    print("\t".join(r[c] for c in cl.COLUMNS))
        if a.section_map:
            for src, ids in sorted(section_map(rows).items()):
                print("%s -> %s" % (src, ", ".join(ids)))
        if a.view or a.section_map:
            return 0
    return _report(check(root, a.register, a.lua_dir, a.register_only, a.partial, a.allow_provisional, a.archive))


def _report(findings):
    for f in sorted(findings, key=lambda f: (f.path, f.line, f.rule)):
        print("%s:%d: %s: %s%s" % (f.path, f.line, f.rule, f.detail, " (warning)" if is_warning(f) else ""))
    n_err = sum(1 for f in findings if not is_warning(f)); n_warn = len(findings) - n_err
    print("%d findings, %d warnings" % (n_err, n_warn))
    return exit_code(findings)


if __name__ == "__main__":
    sys.exit(main())
