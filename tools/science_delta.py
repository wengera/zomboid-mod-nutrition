#!/usr/bin/env python3
"""Apply a science task's part file to the science register, or change one row's status.

A part file has the register's header exactly; every row's id is provisional `S<task>.<n>`. `apply`
validates every row first (a bad row aborts before anything is written, naming its line), mints the
next free id for each in file order, appends them, and prints `S2.1 -> S0042` per row. `status`
changes one row's status and, when superseded, its successor; a row already superseded is refused,
so a lineage is never overwritten. Nothing is ever deleted.

Usage: python tools/science_delta.py apply <part.tsv> [--register TSV] [--dry-run]
       python tools/science_delta.py status <Sdddd> <status> [--successor Sdddd] [--register TSV]"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sciencelib as sl

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO_ROOT, "docs", "reference", "science.tsv")


class DeltaError(Exception):
    pass


def apply(part_path, register=REGISTER, dry_run=False):
    rows = sl.read_register(register)
    part = sl.read_register(part_path)
    nxt = max((sl.id_int(r["id"]) for r in rows), default=0) + 1
    changes, seen = [], set()
    for n, r in enumerate(part, 2):
        if not sl.PROVISIONAL_RX.match(r["id"]):
            raise DeltaError("%s line %d: id %r must be provisional S<task>.<n>" % (part_path, n, r["id"]))
        if r["id"] in seen:
            raise DeltaError("%s line %d: provisional id %s used twice" % (part_path, n, r["id"]))
        seen.add(r["id"])
        errs = sl.validate_row(r, provisional=True)
        if errs:
            raise DeltaError("%s line %d: %s" % (part_path, n, "; ".join(errs)))
    for r in part:
        new = dict(r); new["id"] = sl.id_str(nxt)
        changes.append("%s -> %s" % (r["id"], new["id"]))
        rows.append(new); nxt += 1
    if not dry_run:
        sl.write_register(register, rows)
    return changes


def status(rid, new_status, successor="", register=REGISTER):
    rows = sl.read_register(register)
    by = {r["id"]: r for r in rows}
    if rid not in by:
        raise DeltaError("status %s: no such row" % rid)
    row = by[rid]
    if row["status"] == "superseded":
        raise DeltaError("status %s: row is already superseded (successor %s)" % (rid, row["successor"]))
    row["status"] = new_status
    row["successor"] = successor if new_status == "superseded" else ""
    errs = sl.validate_row(row)
    if errs:
        raise DeltaError("status %s: %s" % (rid, "; ".join(errs)))
    if successor and successor not in by:
        raise DeltaError("status %s: successor %s is not in the register" % (rid, successor))
    sl.write_register(register, rows)
    return "%s status -> %s%s" % (rid, new_status, " (successor %s)" % successor if successor else "")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("apply"); a.add_argument("part"); a.add_argument("--register", default=REGISTER); a.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("status"); s.add_argument("id"); s.add_argument("status"); s.add_argument("--successor", default=""); s.add_argument("--register", default=REGISTER)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "apply":
            changes = apply(args.part, register=args.register, dry_run=args.dry_run)
            for c in changes:
                print(c)
            print("rows: %d%s" % (len(changes), " (dry run)" if args.dry_run else ""))
        else:
            print(status(args.id, args.status, successor=args.successor, register=args.register))
    except (DeltaError, sl.RegisterError, OSError) as e:
        print("error: %s" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
