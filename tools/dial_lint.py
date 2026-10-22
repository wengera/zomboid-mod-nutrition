#!/usr/bin/env python3
"""The dial lint (Plan 19 Task 2; spec Part A, "The lint"; dial-inventory section 3.5): a tunable magnitude left
outside the dial registry, and a dial read the wrong way.

    python tools/dial_lint.py [paths...]        (default: the mod's Lua) exit 1 on any E finding

Scope: NR_Kernel*.lua, NR_Server_*.lua and NR_Client_*.lua under the paths; the registry, the generated and the
declarative data (NR_Data_*.lua) and the bench fixture (NR_Server_Bench.lua) are out of it.

  E1 unregistered dial    a top-level assignment (column 0), or an element line of a top-level constant table,
                          whose value is a numeric literal, a numeric expression or a table of them, and whose
                          comment carries a provenance marker (S1234, #1234, game choice, fitted, inference,
                          design-phase), unless the comment says VANILLA, no row needed or @fixed
  E2 unlabelled constant  a top-level numeric constant with no comment on its line and no comment line above it
  E3 name mismatch        a dial resolved into a local (local X = K.dials.get, ruling T1-1);
                          K.<a>.<b> = K.dials.get("<c>.<d>") where a.b is not c.d; for an adapter's table T,
                          T.<name> = K.dials.get("<dom>.<name2>") where name is not name2, or one table read from two
                          domains in a file
  E4 lookup in a body     K.dials.get or K.dials.row inside a function body (resolved at load only, Rule 6), except
                          inside the resolver's own functions (function K.dials.*)
  W1 probable inline dial a numeric literal other than 0, 1, 2, 0.5, 60, 24, 3600, 1e-6, ln 2 or 2 pi inside a
                          function body on a line whose comment says game choice or names an S id (a warning only)

Not a section 3 gate until the migration's last wave (W10) marks the vanilla mirrors VANILLA. Stdlib only; read-only.
"""
import argparse
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kahlua_lint import strip, lua_files  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")

Finding = collections.namedtuple("Finding", "path line rule detail")

PROVENANCE_RX = re.compile(r"\bS\d{4}\b|#\d{4}\b|game choice|\bfitted\b|\binference\b|design-phase")
EXEMPT_RX = re.compile(r"VANILLA|no row needed|@fixed")
W1_MARK_RX = re.compile(r"game choice|\bS\d{4}\b")
ASSIGN_RX = re.compile(r"^(?:local\s+)?([A-Za-z_][\w.]*)\s*=\s*(.*)$")
GET_RX = re.compile(r"^([A-Za-z_][\w.]*)\s*=\s*K\.dials\.get\(\s*[\"']([^\"']+)[\"']\s*\)\s*$")
LOCAL_GET_RX = re.compile(r"^local\s+[A-Za-z_]\w*\s*=\s*K\.dials\.get\(")
LOOKUP_RX = re.compile(r"\bK\.dials\.(?:get|row)\s*\(")
NUM_RX = re.compile(r"(?<![\w.])(?:\d+\.?\d*(?:[eE][-+]?\d+)?|\.\d+(?:[eE][-+]?\d+)?)(?![\w.])")
KEY_RX = re.compile(r"\[\s*\d+\s*\]\s*=|\b[A-Za-z_]\w*\s*=")
OPENERS_RX = re.compile(r"\b(function|if|do|repeat|end|until)\b")
DIALS_FUNC_RX = re.compile(r"^\s*function\s+(?:K|NutritionRevamp\.kernel)\.dials\.")
TRIVIAL = {0.0, 1.0, 2.0, 0.5, 60.0, 24.0, 3600.0, 1e-6, 0.6931471805599453, 6.283185307179586}


def in_scope(path):
    base = os.path.basename(path)
    if base.startswith("NR_Data_") or base == "NR_Server_Bench.lua":
        return False
    return base.startswith(("NR_Kernel", "NR_Server_", "NR_Client_"))


def numeric_value(rhs):
    """Whether rhs (code, comment stripped) is a numeric literal, a numeric expression or a table of them."""
    body = KEY_RX.sub(" ", rhs.strip().rstrip(","))
    if not body or not re.search(r"\d", body):
        return False
    return re.fullmatch(r"[-+*/().,{}\s\deE]+", body) is not None


def _comment(raw, code):
    rest = raw[len(code):]
    i = rest.find("--")
    return rest[i + 2:].strip() if i >= 0 else ""


def _depth_step(code, stack):
    """Walk the block keywords of one stripped line, pushing and popping the block stack (a function opens a body)."""
    words = OPENERS_RX.findall(code)
    for w in words:
        if w in ("function", "if", "repeat"):
            stack.append(w)
        elif w == "do":
            stack.append("do")
        elif w in ("end", "until") and stack:
            stack.pop()


def lint_text(path, text):
    out = []
    raw_lines = text.split("\n")
    code_lines = strip(text).split("\n")
    stack = []                 # the open blocks before the current line
    dials_body = []            # per open function: whether it is one of K.dials' own
    table_depth = 0            # brace depth inside a top-level constant table
    table_exempt = False       # the table's own line says VANILLA, no row needed or @fixed
    table_owner = {}           # adapter table -> the domain its first get named
    prev_comment_only = False
    for n, (raw, code) in enumerate(zip(raw_lines, code_lines), 1):
        comment = _comment(raw, code)
        in_function = "function" in stack
        stripped = code.strip()
        # E4: a lookup inside a function body that is not the resolver's own
        if in_function and LOOKUP_RX.search(code) and not any(dials_body):
            out.append(Finding(path, n, "E4", "K.dials lookup inside a function body: resolve it at load"))
        # W1: a probable inline dial
        if in_function and W1_MARK_RX.search(comment):
            for m in NUM_RX.finditer(code):
                v = float(m.group(0))
                if v not in TRIVIAL:
                    out.append(Finding(path, n, "W1", "inline literal %s on a line whose comment names a source" % m.group(0)))
                    break
        if table_depth > 0:
            # an element line of a top-level constant table
            if numeric_value(code) and PROVENANCE_RX.search(comment) and not EXEMPT_RX.search(comment) and not table_exempt:
                out.append(Finding(path, n, "E1", "a table element with a provenance comment outside the registry"))
            table_depth += code.count("{") - code.count("}")
        elif not in_function and raw[:1] not in (" ", "\t", "") and not stripped.startswith("function"):
            g = GET_RX.match(raw[:len(code)].strip())      # the raw code: strip() blanks the id string
            a = ASSIGN_RX.match(stripped)
            if LOCAL_GET_RX.match(raw[:len(code)].strip()):
                out.append(Finding(path, n, "E3", "a dial resolved into a local: resolve it into its kernel field (ruling T1-1)"))
            elif g:
                out.extend(_e3(path, n, g.group(1), g.group(2), table_owner))
            elif a and numeric_value(a.group(2)):
                marked = PROVENANCE_RX.search(comment) and not EXEMPT_RX.search(comment)
                if marked:
                    out.append(Finding(path, n, "E1", "%s holds a magnitude with a provenance comment outside the registry" % a.group(1)))
                elif not comment and not prev_comment_only:
                    out.append(Finding(path, n, "E2", "%s: a numeric constant with no comment" % a.group(1)))
                if code.count("{") > code.count("}"):
                    # a multi-line table opened on this line: E1 scans its element lines, and the opening line's own
                    # label answers only that line's E2, exempting no element (Plan 19 Task 3a review I2)
                    table_depth = code.count("{") - code.count("}")
                    table_exempt = False
            elif a and a.group(2).strip().startswith("{") and code.count("{") > code.count("}"):
                table_depth = code.count("{") - code.count("}")
                table_exempt = EXEMPT_RX.search(comment) is not None
        # the block stack, after the line's own checks
        before = len(stack)
        _depth_step(code, stack)
        if len(stack) > before and stack[-1] == "function":
            dials_body.append(bool(DIALS_FUNC_RX.match(code)))
        while len(dials_body) > stack.count("function"):
            dials_body.pop()
        prev_comment_only = stripped == "" and raw.strip().startswith("--")
    return out


def _e3(path, n, lhs, dial_id, table_owner):
    out = []
    parts = lhs.split(".")
    dom, _, name = dial_id.partition(".")
    if parts[0] in ("K", "NutritionRevamp"):
        field = ".".join(parts[1:]) if parts[0] == "K" else ".".join(parts[2:])
        if "." not in field:
            field = "core." + field                # the core domain is K's own top level (core.HEIGHT_M is K.HEIGHT_M)
        if field != dial_id:
            out.append(Finding(path, n, "E3", "%s reads dial %s: the field and the id differ" % (lhs, dial_id)))
        return out
    tail = ".".join(parts[1:])
    if tail != name:
        out.append(Finding(path, n, "E3", "%s reads dial %s: the field and the id differ" % (lhs, dial_id)))
    owner = table_owner.setdefault(parts[0], dom)
    if owner != dom:
        out.append(Finding(path, n, "E3", "%s reads domain %s, and the file read %s for %s before" % (lhs, dom, owner, parts[0])))
    return out


def lint(paths):
    found = []
    for path in lua_files(paths):
        if not in_scope(path):
            continue
        with open(path, encoding="utf-8", errors="replace", newline="") as fh:
            found.extend(lint_text(path.replace("\\", "/"), fh.read().replace("\r\n", "\n")))
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description="Flag tunable magnitudes outside the dial registry.")
    ap.add_argument("paths", nargs="*", default=[DEFAULT])
    ap.add_argument("--summary", action="store_true", help="print the counts by rule and file only")
    args = ap.parse_args(argv)
    found = lint(args.paths)
    if args.summary:
        by = collections.Counter((os.path.basename(f.path), f.rule) for f in found)
        for (base, rule), c in sorted(by.items()):
            print("%-34s %s %d" % (base, rule, c))
    else:
        for f in found:
            print("%s:%d: %s %s" % (f.path, f.line, f.rule, f.detail))
    errors = sum(1 for f in found if f.rule.startswith("E"))
    print("%d errors, %d warnings" % (errors, len(found) - errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
