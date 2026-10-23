#!/usr/bin/env python3
"""The comment-id lint (Plan 20 Task 1, ruling P20-T1-8): a dial-reading line's provenance comment names only
what its registry row's src names.

    python tools/comment_id_lint.py <dir> [--registry NR_Data_Dials.lua]     exit 1 on any finding

For each Lua line under <dir> (the registry itself aside) that calls K.dials.get("<id>") and carries a trailing
comment:
  ID   every #dddd or Sdddd token in the comment must appear in the src of a row the line reads (several gets on
       one line pool their rows' srcs; a `same` row adds the src of the dial it resolves to);
  GC   a comment that says `game choice` needs a row on the line whose src says `game choice`.
A get naming no row is left to tools/dials.py check. The registry is read through dials.py's loader (lupa); by
default it is <dir>'s own NR_Data_Dials.lua, else the repository's. A report until Plan 20 Task 6 makes it a gate.
Stdlib and lupa only; read-only.
"""
import argparse
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dials  # noqa: E402
from kahlua_lint import strip, lua_files  # noqa: E402

REGISTRY_NAME = "NR_Data_Dials.lua"
TOKEN_RX = re.compile(r"(?<![\w#])(#\d{4}|S\d{4})(?!\d)")
GAME_CHOICE = "game choice"

Finding = collections.namedtuple("Finding", "path line rule detail")


def _comment(raw, code):
    """The trailing comment of a raw line whose comment- and string-stripped form is `code`."""
    rest = raw[len(code.rstrip()):]
    i = rest.find("--")
    return rest[i + 2:].strip() if i >= 0 else ""


def _srcs(rows, dial_id):
    """The src text of a dial and of the dial its `same` chain resolves to; None for an unknown dial."""
    if dial_id not in rows:
        return None
    out = [str(rows[dial_id].get("src", ""))]
    end, _ = dials._resolve(rows, dial_id)
    if end and end != dial_id:
        out.append(str(rows[end].get("src", "")))
    return " ".join(out)


def lint_text(path, text, rows):
    out = []
    raw_lines = text.split("\n")
    code_lines = strip(text).split("\n")
    for n, (raw, code) in enumerate(zip(raw_lines, code_lines), 1):
        if "--" not in raw[len(code.rstrip()):]:
            continue
        ids = dials.GET_RX.findall(raw[:len(code.rstrip())])
        if not ids:
            continue
        comment = _comment(raw, code)
        srcs = [s for s in (_srcs(rows, i) for i in ids) if s is not None]
        if not srcs:
            continue
        pool = " ".join(srcs)
        have = set(TOKEN_RX.findall(pool))
        for tok in dict.fromkeys(TOKEN_RX.findall(comment)):
            if tok not in have:
                out.append(Finding(path, n, "ID", "%s is not in the src of %s" % (tok, ", ".join(ids))))
        if GAME_CHOICE in comment and GAME_CHOICE not in pool:
            out.append(Finding(path, n, "GC", "the comment says game choice; the src of %s does not" % ", ".join(ids)))
    return out


def registry_path(directory, registry=None):
    if registry:
        return registry
    for root, _, files in os.walk(directory):
        if REGISTRY_NAME in files:
            return os.path.join(root, REGISTRY_NAME)
    return os.path.join(dials.REPO, *dials.REGISTRY_REL.split("/"))


def lint(directory, registry=None):
    reg = registry_path(directory, registry)
    rows = dials.load_rows(dials._read(reg))
    found = []
    for path in lua_files([directory]):
        if os.path.basename(path) == REGISTRY_NAME:
            continue
        with open(path, encoding="utf-8", errors="replace", newline="") as fh:
            found.extend(lint_text(path.replace("\\", "/"), fh.read().replace("\r\n", "\n"), rows))
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("--registry")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.dir):
        print("%s: no such directory" % a.dir)
        return 2
    found = lint(a.dir, a.registry)
    for f in found:
        print("%s:%d: %s: %s" % f)
    print("%d findings" % len(found))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
