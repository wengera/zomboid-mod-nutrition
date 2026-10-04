#!/usr/bin/env python3
"""Apply a science task's part file to the science register, or change one row's status.

A part file has the register's header exactly; every row's id is provisional `S<task>.<n>`. `apply`
validates every row first (a bad row aborts before anything is written, naming its line), mints the
next free id for each in file order, appends them, and prints `S2.1 -> S0042` per row. `status`
changes one row's status and, when superseded, its successor; a row already superseded is refused,
so a lineage is never overwritten. Nothing is ever deleted.

Usage: python tools/science_delta.py apply <part.tsv> [--register TSV] [--dry-run] [--allow-duplicate]
       python tools/science_delta.py status <Sdddd> <status> [--successor Sdddd[, Sdddd]] [--register TSV]
       python tools/science_delta.py settle <Sdddd> --topic T --grade G --value V --citation C [--range R] [--population P] [--status unverified] [--register TSV]"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sciencelib as sl

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO_ROOT, "docs", "reference", "science.tsv")


class DeltaError(Exception):
    pass


def apply(part_path, register=REGISTER, dry_run=False, allow_duplicate=False):
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
        if not allow_duplicate:
            for old in rows:
                if (old["parameter"], old["citation"], old["source"]) == (r["parameter"], r["citation"], r["source"]):
                    raise DeltaError("%s line %d: %s repeats %s (same parameter, citation and source); a part file is applied once, or pass --allow-duplicate" % (part_path, n, r["id"], old["id"]))
    for r in part:
        new = dict(r); new["id"] = sl.id_str(nxt)
        changes.append("%s -> %s" % (r["id"], new["id"]))
        rows.append(new); nxt += 1
    if not dry_run:
        sl.write_register(register, rows)
    return changes


def settle(rid, topic, grade, value, citation, range="", population="", new_status="settled", register=REGISTER):
    """Fill an open row's cells and move it to settled (or unverified); the result is validated first."""
    rows = sl.read_register(register)
    by = {r["id"]: r for r in rows}
    if rid not in by:
        raise DeltaError("settle %s: no such row" % rid)
    row = by[rid]
    if row["status"] != "open":
        raise DeltaError("settle %s: row is %s, only an open row is settled" % (rid, row["status"]))
    if new_status not in ("settled", "unverified"):
        raise DeltaError("settle %s: status must be settled or unverified" % rid)
    try:
        grade = sl.resolve_grade(grade)
    except ValueError as e:
        raise DeltaError("settle %s: %s" % (rid, e))
    row.update(topic=topic, grade=grade, value=value, citation=citation, status=new_status)
    if range:
        row["range"] = range
    if population:
        row["population"] = population
    errs = sl.validate_row(row)
    if errs:
        raise DeltaError("settle %s: %s" % (rid, "; ".join(errs)))
    sl.write_register(register, rows)
    return "%s %s" % (rid, new_status)


def status(rid, new_status, successor="", register=REGISTER):
    rows = sl.read_register(register)
    by = {r["id"]: r for r in rows}
    if rid not in by:
        raise DeltaError("status %s: no such row" % rid)
    row = by[rid]
    if row["status"] == "superseded":
        raise DeltaError("status %s: row is already superseded (successor %s)" % (rid, row["successor"]))
    if successor and new_status != "superseded":
        raise DeltaError("status %s: --successor only with superseded" % rid)
    succs = [s.strip() for s in successor.split(",") if s.strip()]
    for s in succs:
        if s == rid:
            raise DeltaError("status %s: a row cannot succeed itself" % rid)
        if s not in by:
            raise DeltaError("status %s: successor %s is not in the register" % (rid, s))
        if by[s]["status"] == "superseded":
            raise DeltaError("status %s: successor %s is itself superseded" % (rid, s))
    successor = ", ".join(succs)
    row["status"] = new_status
    row["successor"] = successor if new_status == "superseded" else ""
    errs = sl.validate_row(row)
    if errs:
        raise DeltaError("status %s: %s" % (rid, "; ".join(errs)))
    sl.write_register(register, rows)
    return "%s status -> %s%s" % (rid, new_status, " (successor %s)" % successor if successor else "")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("apply"); a.add_argument("part"); a.add_argument("--register", default=REGISTER); a.add_argument("--dry-run", action="store_true"); a.add_argument("--allow-duplicate", action="store_true")
    g = sub.add_parser("settle"); g.add_argument("id"); g.add_argument("--topic", required=True); g.add_argument("--grade", required=True)
    g.add_argument("--value", required=True); g.add_argument("--range", default=""); g.add_argument("--population", default="")
    g.add_argument("--citation", required=True); g.add_argument("--status", default="settled", dest="new_status"); g.add_argument("--register", default=REGISTER)
    s = sub.add_parser("status"); s.add_argument("id"); s.add_argument("status"); s.add_argument("--successor", default=""); s.add_argument("--register", default=REGISTER)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "apply":
            changes = apply(args.part, register=args.register, dry_run=args.dry_run, allow_duplicate=args.allow_duplicate)
            for c in changes:
                print(c)
            print("rows: %d%s" % (len(changes), " (dry run)" if args.dry_run else ""))
        elif args.cmd == "settle":
            print(settle(args.id, args.topic, args.grade, args.value, args.citation, range=args.range, population=args.population,
                         new_status=args.new_status, register=args.register))
        else:
            print(status(args.id, args.status, successor=args.successor, register=args.register))
    except (DeltaError, sl.RegisterError, OSError) as e:
        print("error: %s" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
