#!/usr/bin/env python3
"""Apply a page task's claims delta to the register (spec § The claims register, "Deltas in Phases 2 and 3").

A delta file is tab-separated with the header
  op  id  claim  grade  pointer  bound  status  successor  kind  source  owner  reason
and one delta per line. `add` names a provisional id `T<task>.<n>`: apply mints the next free register
id for it and rewrites that provisional tag in every page named with --pages. `split` names a real
parent id and is followed by exactly two `add` lines, which become the parent's successors; the parent
goes superseded and its tag on the pages is rewritten to the two children. `supersede` names a real
parent id and its single successor is the `add` its `successor` cell names (a provisional id, wherever
that add sits in the file; one no add carries is refused), or, when the cell is empty, the `add` line
directly after it; the parent goes superseded and its tag on the pages is rewritten to the child. A supersession onto a row
that already exists is `status` with a real successor, which rewrites no tag. `retarget` changes the
row's owner. `status` changes the row's status (and its successor when superseded; its bound when
the delta gives one). Nothing is ever deleted; an invalid delta aborts before anything is written,
and an op against a row that is already superseded is refused, so a lineage is never overwritten.
Tag rewriting is textual, exactly as `claims_check --fix-tags` is: a tag bracket inside a code span
or a fenced block is rewritten with the rest, so a provisional id quoted in a code span is applied too.

The archive (docs/reference/claims-archive.tsv, beside the register; Plan 20) shares the register's id space:
an add mints past the highest id of both files, and an op naming an archived row is refused. `retire` names a
live row and needs its `reason` cell: the row goes `retired`, every unpinned `repo:` pointer is pinned at HEAD's
short sha (each pinned quote must hold at HEAD, or nothing is written), its bound gains
`; retired <YYYY-MM-DD>: <reason>`, and the row moves to the archive (ruling P20-T1-4); a page still tagging it
is noted, and claims_check fails it. A `status` delta never writes `retired`.

Usage: python tools/claims_delta.py apply <delta.tsv> --pages <page.md> [...] [--register TSV] [--archive TSV] [--dry-run]
       python tools/claims_delta.py archive-superseded [--register TSV] [--archive TSV] [--dry-run]
archive-superseded moves every superseded row of the register to the archive, the archive kept in id order
(ruling P20-T1-5); --dry-run prints the count and writes nothing."""
import argparse, datetime, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claimslib as cl

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO_ROOT, "docs", "reference", "claims.tsv")
DELTA_COLUMNS = ("op",) + cl.COLUMNS + ("reason",)
ARCHIVE_NAME = "claims-archive.tsv"
OPS = ("add", "retarget", "status", "split", "supersede", "retire")


class DeltaError(Exception):
    pass


def read_delta(path):
    with open(path, encoding="utf-8", newline="") as f:
        lines = [l.rstrip("\r") for l in f.read().split("\n")]
    if not lines or lines[0].split("\t") != list(DELTA_COLUMNS):
        raise DeltaError("%s: header must be %s" % (path, "\t".join(DELTA_COLUMNS)))
    out = []
    for n, line in enumerate(lines[1:], 2):
        if not line.strip():
            continue
        cells = line.split("\t")
        if len(cells) != len(DELTA_COLUMNS):
            raise DeltaError("%s:%d: %d cells, expected %d" % (path, n, len(cells), len(DELTA_COLUMNS)))
        d = dict(zip(DELTA_COLUMNS, cells))
        if d["op"] not in OPS:
            raise DeltaError("%s:%d: unknown op %r" % (path, n, d["op"]))
        out.append(d)
    return out


def _next_id(rows):
    return cl.id_str(max((cl.id_int(r["id"]) for r in rows), default=0) + 1)


def archive_path(register):
    """The archive beside a register: docs/reference/claims-archive.tsv for the real one."""
    return os.path.join(os.path.dirname(os.path.abspath(register)), ARCHIVE_NAME)


def read_archive(path):
    """The archive's rows; an absent archive is an empty one."""
    return cl.read_register(path) if os.path.exists(path) else []


def _by_id(rows):
    return sorted(rows, key=lambda r: cl.id_int(r["id"]))


def _mint(d, new_rows, tag_map, note="", archive=()):
    if not cl.is_provisional(d["id"]):
        raise DeltaError("add %s: id must be provisional (T<task>.<n>)" % d["id"])
    if d["id"] in tag_map:
        raise DeltaError("add %s: provisional id used twice" % d["id"])
    row = {c: d[c] for c in cl.COLUMNS}
    row["id"] = _next_id(list(new_rows) + list(archive))
    errs = cl.validate_row(row)
    if errs:
        raise DeltaError("add %s: %s" % (d["id"], "; ".join(errs)))
    new_rows.append(row)
    tag_map[d["id"]] = row["id"]
    return row, "%s -> %s%s" % (d["id"], row["id"], note)


def _target(op, cid, by, archived=()):
    """The row an op names: a missing row is an error, and so is an archived one or one whose lineage is already
    closed."""
    row = by.get(cid)
    if row is None and cid in archived:
        raise DeltaError("%s %s: row is archived (%s)" % (op, cid, ARCHIVE_NAME))
    if row is None:
        raise DeltaError("%s %s: no such row" % (op, cid))
    if row.get("status") == "superseded":
        raise DeltaError("%s %s: row is already superseded (successor %s)" % (op, cid, row.get("successor", "")))
    return row


def plan(rows, deltas, archive=(), today=None, head=None):
    """(new_rows, tag_map, changes, new_archive) with nothing written; raises DeltaError on the first bad delta.
    `today` (YYYY-MM-DD) and `head` (a short sha, or a callable returning one) serve a retire."""
    new_rows = [dict(r) for r in rows]
    new_arch = [dict(r) for r in archive]
    archived = {r["id"] for r in new_arch}
    by = {r["id"]: r for r in new_rows}
    tag_map, changes, i = {}, [], 0
    claimed = set()                            # adds a supersede minted ahead of their own line
    while i < len(deltas):
        d = deltas[i]
        if d["op"] == "add" and d["id"] in claimed:
            i += 1
        elif d["op"] == "add":
            row, msg = _mint(d, new_rows, tag_map, archive=new_arch)
            by[row["id"]] = row
            changes.append(msg)
            i += 1
        elif d["op"] == "split":
            parent = _target("split", d["id"], by, archived)
            kids = deltas[i + 1:i + 3]
            if len(kids) != 2 or any(k["op"] != "add" for k in kids):
                raise DeltaError("split %s: must be followed by exactly two add lines" % d["id"])
            ids = []
            for k in kids:
                row, msg = _mint(k, new_rows, tag_map, " (split of %s)" % d["id"], new_arch)
                by[row["id"]] = row
                ids.append(row["id"])
                changes.append(msg)
            parent["status"], parent["successor"] = "superseded", ", ".join(ids)
            tag_map[d["id"]] = parent["successor"]
            changes.append("%s superseded -> %s" % (d["id"], parent["successor"]))
            i += 3
        elif d["op"] == "supersede":
            parent = _target("supersede", d["id"], by, archived)
            named = d["successor"].strip()
            if named:
                if not cl.is_provisional(named):
                    raise DeltaError("supersede %s: successor cell %r is not a provisional id (T<task>.<n>)" % (d["id"], named))
                hits = [k for k in deltas if k["op"] == "add" and k["id"] == named]
                if len(hits) != 1:
                    raise DeltaError("supersede %s: successor %s is carried by no add row" % (d["id"], named))
                kid, step = hits[0], 1
                if i + 1 < len(deltas) and deltas[i + 1] is kid:
                    step = 2                   # the named add sits directly after: consumed here
            else:
                nxt = deltas[i + 1:i + 2]
                if len(nxt) != 1 or nxt[0]["op"] != "add":
                    raise DeltaError("supersede %s: must be followed by exactly one add line" % d["id"])
                kid, step = nxt[0], 2
            if kid["id"] in tag_map:
                row = by[tag_map[kid["id"]]]
            else:
                row, msg = _mint(kid, new_rows, tag_map, " (successor of %s)" % d["id"], new_arch)
                by[row["id"]] = row
                changes.append(msg)
                claimed.add(kid["id"])
            parent["status"], parent["successor"] = "superseded", row["id"]
            tag_map[d["id"]] = row["id"]
            changes.append("%s superseded -> %s" % (d["id"], row["id"]))
            i += step
        elif d["op"] == "retarget":
            row = _target("retarget", d["id"], by, archived)
            if not cl.OWNER_RX.match(d["owner"]):
                raise DeltaError("retarget %s: owner %r is not <layer>/<page>.md#<anchor>" % (d["id"], d["owner"]))
            changes.append("%s owner %s -> %s" % (d["id"], row["owner"], d["owner"]))
            row["owner"] = d["owner"]
            i += 1
        elif d["op"] == "retire":
            row = _target("retire", d["id"], by, archived)
            reason = d["reason"].strip()
            if not reason:
                raise DeltaError("retire %s: the reason cell is empty; a retirement names why" % d["id"])
            sha = head() if callable(head) else head
            if not sha:
                raise DeltaError("retire %s: no HEAD commit to pin the repo: pointers at" % d["id"])
            try:
                row["pointer"] = cl.pin_repo_pointers(row["pointer"], sha)
            except ValueError as e:
                raise DeltaError("retire %s: %s" % (d["id"], e))
            day = today or datetime.date.today().isoformat()
            row["bound"] = "%s; retired %s: %s" % (row["bound"].strip() or "none", day, reason)
            row["status"] = "retired"
            errs = cl.validate_row(row)
            if errs:
                raise DeltaError("retire %s: %s" % (d["id"], "; ".join(errs)))
            new_rows.remove(row)
            del by[row["id"]]
            new_arch.append(row)
            archived.add(row["id"])
            changes.append("%s retired -> %s" % (d["id"], ARCHIVE_NAME))
            i += 1
        else:
            row = _target("status", d["id"], by, archived)
            if d["status"] == "retired":
                raise DeltaError("status %s: a row is retired only by the retire op, which moves it to the archive" % d["id"])
            if d["status"] not in cl.STATUSES:
                raise DeltaError("status %s: %r not in %s" % (d["id"], d["status"], cl.STATUSES))
            row["status"] = d["status"]
            row["successor"] = d["successor"] if d["status"] == "superseded" else ""
            if d["bound"]:
                row["bound"] = d["bound"]
            errs = cl.validate_row(row)
            if errs:
                raise DeltaError("status %s: %s" % (d["id"], "; ".join(errs)))
            changes.append("%s status -> %s" % (d["id"], d["status"]))
            i += 1
    return new_rows, tag_map, changes, _by_id(new_arch)


def rewrite_page(text, tag_map, by_id):
    """Rewrites every tag bracket naming a mapped id (a provisional id, or a split parent) and re-canonicalises it."""
    def fix(m):
        bracket = m.group(0)
        if not (cl.TAG_RX.match(bracket) or cl.find_provisional(bracket)):
            return bracket                     # a markdown link or plain brackets
        items = []
        for cid, suffix in cl.split_tag(m.group(1)):
            for t in [x.strip() for x in tag_map.get(cid, cid).split(",")]:
                items.append(t + (cl.canonical_suffix(by_id[t]) if t in by_id else suffix))
        return "[" + ", ".join(dict.fromkeys(items)) + "]"
    return cl.BRACKET_RX.sub(fix, text)


def _git(cwd, *args):
    try:
        p = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout.strip() if p.returncode == 0 else None


def head_sha(register):
    """HEAD's short sha in the repository holding the register, or None."""
    return _git(os.path.dirname(os.path.abspath(register)), "rev-parse", "--short", "HEAD")


def _check_pins(retired, register):
    """Each retired row's pinned repo: pointers resolve and quote their line at the pin, read as claims_check reads
    them; a DeltaError naming every miss otherwise (a file edited since HEAD, a stale quote)."""
    import claims_check as cc
    root = _git(os.path.dirname(os.path.abspath(register)), "rev-parse", "--show-toplevel")
    if root is None:
        raise DeltaError("retire: the register is not inside a git repository")
    probes = []
    for r in retired:
        repo = [p for p in cl._split_outside_quotes(r["pointer"]) if p.strip().startswith("repo:")]
        if repo:
            probes.append(dict(r, pointer=";".join(repo)))
    misses = cc.rule_pointer(probes, root, ARCHIVE_NAME, archived=True)
    if misses:
        raise DeltaError("retire: a pinned pointer does not hold at HEAD: " + "; ".join(f.detail for f in misses))


def apply(delta_path, pages, register=REGISTER, dry_run=False, archive=None, today=None):
    archive = archive or archive_path(register)
    rows, arch = cl.read_register(register), read_archive(archive)
    new_rows, tag_map, changes, new_arch = plan(rows, read_delta(delta_path), arch, today, lambda: head_sha(register))
    before = {r["id"] for r in arch}
    retired = [r for r in new_arch if r["id"] not in before]
    if retired:
        _check_pins(retired, register)
    by_id = {r["id"]: r for r in new_rows}
    rewritten = {}
    for p in pages:
        with open(p, encoding="utf-8", newline="") as f:
            text = f.read()
        new = rewrite_page(text, tag_map, by_id)
        if new != text:
            rewritten[p] = new
    if not dry_run:
        cl.write_register(register, new_rows)
        if retired:
            cl.write_register(archive, new_arch)
        for p, text in rewritten.items():
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(text)
    return changes, sorted(rewritten)


def archive_superseded(register=REGISTER, archive=None, dry_run=False):
    """Move every superseded row of the register to the archive, the archive kept in id order (P20-T1-5). Returns
    the number moved; dry_run writes nothing."""
    archive = archive or archive_path(register)
    rows, arch = cl.read_register(register), read_archive(archive)
    moved = [r for r in rows if r["status"] == "superseded"]
    taken = {r["id"] for r in arch}
    clash = [r["id"] for r in moved if r["id"] in taken]
    if clash:
        raise DeltaError("archive-superseded: %s already in the archive" % ", ".join(clash))
    if moved and not dry_run:
        cl.write_register(archive, _by_id(arch + moved))
        cl.write_register(register, [r for r in rows if r["status"] != "superseded"])
    return len(moved)


def _owner_page(owner):
    return owner.split("#", 1)[0]


def _named(pages, owner_page):
    """True when one of the --pages paths is that owner page (`facts/x.md` matches `docs/facts/x.md`)."""
    for p in pages:
        q = p.replace("\\", "/")
        if q == owner_page or q.endswith("/" + owner_page):
            return True
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("apply")
    a.add_argument("delta"); a.add_argument("--pages", nargs="+", required=True)
    a.add_argument("--register", default=REGISTER); a.add_argument("--archive"); a.add_argument("--dry-run", action="store_true")
    z = sub.add_parser("archive-superseded")
    z.add_argument("--register", default=REGISTER); z.add_argument("--archive"); z.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd == "archive-superseded":
        try:
            n = archive_superseded(args.register, args.archive, args.dry_run)
        except (DeltaError, cl.RegisterError, OSError) as e:
            print("error: %s" % e)
            return 1
        where = args.archive or archive_path(args.register)
        print("%d superseded rows %s %s" % (n, "would move to" if args.dry_run else "moved to", where)
              + (" (dry run)" if args.dry_run else ""))
        return 0
    try:
        deltas = read_delta(args.delta)
        changes, pages = apply(args.delta, args.pages, register=args.register, dry_run=args.dry_run, archive=args.archive)
    except (DeltaError, cl.RegisterError, OSError) as e:
        print("error: %s" % e)
        return 1
    for c in changes:
        print(c)
    for d in deltas:
        page = _owner_page(d["owner"])
        if d["op"] == "retarget" and not _named(args.pages, page):
            print("NOTE: %s now owned by %s, which is not among --pages" % (d["id"], page))
        if d["op"] == "retire":
            for p in args.pages:
                with open(p, encoding="utf-8", newline="") as f:
                    if d["id"] in {cid for _, cid, _ in cl.iter_tags(f.read())}:
                        print("NOTE: %s is retired but %s still tags it; claims_check fails that tag" % (d["id"], p))
    print("pages rewritten: %s" % (", ".join(pages) if pages else "none") + (" (dry run)" if args.dry_run else ""))
    for p in args.pages:
        with open(p, encoding="utf-8", newline="") as f:
            left = sorted(set(cl.find_provisional(f.read())))
        if left:
            print("WARNING: provisional tags left on %s: %s" % (p, ", ".join(left)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
