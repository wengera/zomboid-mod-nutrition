#!/usr/bin/env python3
"""Kahlua dialect lint for the mod's Lua and the experiment mods (CLAUDE.md § 5 Kahlua rules).

    python tools/kahlua_lint.py mod testing/experiments

Prints `path:line: rule: detail` per finding and `N findings` last; exits 1 on any finding.
Comments and string literals are blanked first (the shape tools/luabalance.py uses), so a rule
never fires on a word inside either.

| rule          | fires on                                                                 |
|---------------|--------------------------------------------------------------------------|
| `goto`        | the keyword `goto` or a `::label::` -- Kahlua has neither (#0938)        |
| `format-d`    | `%d`, `%i`, `%x`, `%X`, `%o`, `%c` inside a `string.format` call -- the dialect raises on a float (#0939) |
| `java-length` | `#` applied to a call result (`#x:getItems()`, `#getOnlinePlayers()`): a Java list has no length (#0940) |
| `java-pairs`  | `pairs(` or `ipairs(` whose argument is a call result: iterating a Java object raises (#0941) |
| `loadstring`  | `loadstring(` -- removed in 42.20.x (#0960)                              |

Stdlib only; read-only.
"""
import argparse, collections, os, re, sys

Finding = collections.namedtuple("Finding", "path line rule detail")

LONG_OPEN = re.compile(r"(--)?\[(=*)\[")
GOTO_RX = re.compile(r"(?<![\w.])goto\s+\w+|::\s*\w+\s*::")
FORMAT_RX = re.compile(r"string\.format\s*\(")
FORMAT_D_RX = re.compile(r"%[-+ #0]*\d*(?:\.\d+)?[dixXoc]")
LENGTH_CALL_RX = re.compile(r"#\s*[\w.]+(?::\w+)?\s*\(")
PAIRS_CALL_RX = re.compile(r"\bi?pairs\s*\(\s*[\w.]+(?::\w+)?\s*\(")
LOADSTRING_RX = re.compile(r"\bloadstring\s*\(")


def strip(src):
    """Blank comments and string literals, keeping every newline (luabalance.py's shape).
    String bodies are replaced by spaces so column positions and %d inside them vanish."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        m = LONG_OPEN.match(src, i)
        if m and (m.group(1) or src[i] == "["):
            close = "]" + m.group(2) + "]"
            j = src.find(close, m.end())
            j = n if j < 0 else j + len(close)
            out.append("\n" * src.count("\n", i, j))
            i = j
            continue
        if src.startswith("--", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            out.append(c + " " * max(0, j - i - 1) + c)
            i = j + 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def lint_text(path, text):
    found = []
    raw_lines = text.split("\n")
    for n, line in enumerate(strip(text).split("\n"), 1):
        if GOTO_RX.search(line):
            found.append(Finding(path, n, "goto", "Kahlua has no goto and no labels"))
        if FORMAT_RX.search(line):
            # the stripped line's literals are blanked, so look at the raw line's format string
            raw = raw_lines[n - 1]
            if FORMAT_D_RX.search(raw):
                found.append(Finding(path, n, "format-d", "integer conversion of a Lua number raises; use %.0f"))
        if LENGTH_CALL_RX.search(line):
            found.append(Finding(path, n, "java-length", "# on a call result: a Java list has no length; walk size()/get(i)"))
        if PAIRS_CALL_RX.search(line):
            found.append(Finding(path, n, "java-pairs", "pairs over a call result: a Java object raises; walk size()/get(i)"))
        if LOADSTRING_RX.search(line):
            found.append(Finding(path, n, "loadstring", "removed on 42.20.x"))
    return found


def lua_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for f in sorted(files):
                    if f.lower().endswith(".lua"):
                        yield os.path.join(root, f)
        elif p.lower().endswith(".lua"):
            yield p


def lint(paths):
    found = []
    for path in lua_files(paths):
        with open(path, encoding="utf-8", errors="replace", newline="") as fh:
            found.extend(lint_text(path.replace("\\", "/"), fh.read().replace("\r\n", "\n")))
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args(argv)
    found = lint(a.paths)
    for f in found:
        print(f"{f.path}:{f.line}: {f.rule}: {f.detail}")
    print(f"{len(found)} findings")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
