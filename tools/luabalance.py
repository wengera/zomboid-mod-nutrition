#!/usr/bin/env python3
"""Bracket / block-`end` balance read-through for Lua files (slice-08 shape).

Strips long comments, line comments, long strings and quoted strings, then reports the
delta of {} () [] and of block depth, plus the number of lines on which block depth went
negative (an `end` with nothing open -- the shape a missing `function` line makes)."""
import io, os, re, sys

LONG_OPEN = re.compile(r"(--)?\[(=*)\[")


def strip(src):
    """Return the source with comments and string literals blanked (newlines kept)."""
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
            j = n if j < 0 else j
            i = j
            continue
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            i = min(j + 1, n)
            continue
        out.append(c)
        i += 1
    return "".join(out)


TOK = re.compile(r"\b(function|elseif|if|do|end|repeat|until|for|while)\b|[{}()\[\]]")
OPEN = {"function": 1, "if": 1, "do": 1, "repeat": 1}
CLOSE = {"end": 1, "until": 1}


def report(path):
    src = io.open(path, encoding="utf-8", errors="replace").read()
    clean = strip(src)
    pairs = {"{}": 0, "()": 0, "[]": 0}
    depth, neg_lines, seen_neg = 0, 0, False
    for m in TOK.finditer(clean):
        t = m.group(0)
        if t in "{}()[]":
            key = {"{": "{}", "}": "{}", "(": "()", ")": "()", "[": "[]", "]": "[]"}[t]
            pairs[key] += 1 if t in "{([" else -1
        elif t in OPEN:
            depth += 1
        elif t in CLOSE:
            depth -= 1
            if depth < 0 and not seen_neg:
                seen_neg = True
            if depth < 0:
                neg_lines += 1
    ok = depth == 0 and all(v == 0 for v in pairs.values()) and neg_lines == 0
    return (os.path.basename(path), pairs["{}"], pairs["()"], pairs["[]"], depth, neg_lines,
            "BALANCED" if ok else "UNBALANCED")


if __name__ == "__main__":
    rows = [report(p) for p in sys.argv[1:]]
    w = max([len(r[0]) for r in rows] + [1])
    for name, b, p, s, d, neg, verdict in rows:
        print("%-*s  {} %+d  () %+d  [] %+d   end-depth %+d   neg-depth lines %d   %s"
              % (w, name, b, p, s, d, neg, verdict))
    sys.exit(0 if all(r[6] == "BALANCED" for r in rows) else 1)
