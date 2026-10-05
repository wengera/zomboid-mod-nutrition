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

Usage: python tools/claims_delta.py apply <delta.tsv> --pages <page.md> [...] [--register TSV] [--dry-run]"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claimslib as cl

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO_ROOT, "docs", "reference", "claims.tsv")
DELTA_COLUMNS = ("op",) + cl.COLUMNS + ("reason",)
OPS = ("add", "retarget", "status", "split", "supersede")


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


def _mint(d, new_rows, tag_map, note=""):
    if not cl.is_provisional(d["id"]):
        raise DeltaError("add %s: id must be provisional (T<task>.<n>)" % d["id"])
    if d["id"] in tag_map:
        raise DeltaError("add %s: provisional id used twice" % d["id"])
    row = {c: d[c] for c in cl.COLUMNS}
    row["id"] = _next_id(new_rows)
    errs = cl.validate_row(row)
    if errs:
        raise DeltaError("add %s: %s" % (d["id"], "; ".join(errs)))
    new_rows.append(row)
    tag_map[d["id"]] = row["id"]
    return row, "%s -> %s%s" % (d["id"], row["id"], note)


def _target(op, cid, by):
    """The row an op names: a missing row is an error, and so is one whose lineage is already closed."""
    row = by.get(cid)
    if row is None:
        raise DeltaError("%s %s: no such row" % (op, cid))
    if row.get("status") == "superseded":
        raise DeltaError("%s %s: row is already superseded (successor %s)" % (op, cid, row.get("successor", "")))
    return row


def plan(rows, deltas):
    """(new_rows, tag_map, changes) with nothing written; raises DeltaError on the first bad delta."""
    new_rows = [dict(r) for r in rows]
    by = {r["id"]: r for r in new_rows}
    tag_map, changes, i = {}, [], 0
    claimed = set()                            # adds a supersede minted ahead of their own line
    while i < len(deltas):
        d = deltas[i]
        if d["op"] == "add" and d["id"] in claimed:
            i += 1
        elif d["op"] == "add":
            row, msg = _mint(d, new_rows, tag_map)
            by[row["id"]] = row
            changes.append(msg)
            i += 1
        elif d["op"] == "split":
            parent = _target("split", d["id"], by)
            kids = deltas[i + 1:i + 3]
            if len(kids) != 2 or any(k["op"] != "add" for k in kids):
                raise DeltaError("split %s: must be followed by exactly two add lines" % d["id"])
            ids = []
            for k in kids:
                row, msg = _mint(k, new_rows, tag_map, " (split of %s)" % d["id"])
                by[row["id"]] = row
                ids.append(row["id"])
                changes.append(msg)
            parent["status"], parent["successor"] = "superseded", ", ".join(ids)
            tag_map[d["id"]] = parent["successor"]
            changes.append("%s superseded -> %s" % (d["id"], parent["successor"]))
            i += 3
        elif d["op"] == "supersede":
            parent = _target("supersede", d["id"], by)
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
                row, msg = _mint(kid, new_rows, tag_map, " (successor of %s)" % d["id"])
                by[row["id"]] = row
                changes.append(msg)
                claimed.add(kid["id"])
            parent["status"], parent["successor"] = "superseded", row["id"]
            tag_map[d["id"]] = row["id"]
            changes.append("%s superseded -> %s" % (d["id"], row["id"]))
            i += step
        elif d["op"] == "retarget":
            row = _target("retarget", d["id"], by)
            if not cl.OWNER_RX.match(d["owner"]):
                raise DeltaError("retarget %s: owner %r is not <layer>/<page>.md#<anchor>" % (d["id"], d["owner"]))
            changes.append("%s owner %s -> %s" % (d["id"], row["owner"], d["owner"]))
            row["owner"] = d["owner"]
            i += 1
        else:
            row = _target("status", d["id"], by)
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
    return new_rows, tag_map, changes


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


def apply(delta_path, pages, register=REGISTER, dry_run=False):
    rows = cl.read_register(register)
    new_rows, tag_map, changes = plan(rows, read_delta(delta_path))
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
        for p, text in rewritten.items():
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(text)
    return changes, sorted(rewritten)


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
    a.add_argument("--register", default=REGISTER); a.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    try:
        deltas = read_delta(args.delta)
        changes, pages = apply(args.delta, args.pages, register=args.register, dry_run=args.dry_run)
    except (DeltaError, cl.RegisterError, OSError) as e:
        print("error: %s" % e)
        return 1
    for c in changes:
        print(c)
    for d in deltas:
        page = _owner_page(d["owner"])
        if d["op"] == "retarget" and not _named(args.pages, page):
            print("NOTE: %s now owned by %s, which is not among --pages" % (d["id"], page))
    print("pages rewritten: %s" % (", ".join(pages) if pages else "none") + (" (dry run)" if args.dry_run else ""))
    for p in args.pages:
        with open(p, encoding="utf-8", newline="") as f:
            left = sorted(set(cl.find_provisional(f.read())))
        if left:
            print("WARNING: provisional tags left on %s: %s" % (p, ", ".join(left)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
