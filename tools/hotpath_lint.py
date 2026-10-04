#!/usr/bin/env python3
"""Fast-path and kernel-shape lint for the nutrition mod (spec § 6 fast-path rules, § 4.1 kernel).

    python tools/hotpath_lint.py mod

Inside a `-- @fastpath` ... `-- @endfastpath` region (marker comments at the start of a line; any Lua file) a line may not:
  alloc           open a table constructor `{`
  concat          concatenate strings `..`
  pcall           call pcall/xpcall/error/assert -- except ONE line per region carrying `-- @rimguard`
  string          call string.* / tostring / tonumber / table.*
  math            use `^`, math.exp, math.pow, math.log, math.sqrt
  loop            open a for/while/repeat loop
  unhoisted-call  call a method `name:method(` on a receiver not in the file's `-- @hoisted a, b` list
                  (the receiver is the name directly before the colon: `h.stats:get(` is checked as `stats`)
  region          a @fastpath with no @endfastpath, or an @endfastpath with no open region
A file named `NR_Kernel*.lua` (the pure kernel) additionally may not:
  kernel-shape    define a function other than `function NutritionRevamp.kernel.<path>(` /
                  `function K.<path>(` (K the local alias) -- no `local function`, no bare
                  globals, no anonymous functions assigned to fields -- so that
                  debug.getinfo(f, "L").activelines over the kernel table is the whole
                  executable-line set the coverage gate compares against (Plan 1 ruling 3)
  kernel-oneline  put code after `then`, `else`, `do`, `repeat` or a `function ...(...)` header on the same line, or use
                  the value-pick idiom `X and Y or Z` (a line not starting if/elseif/while/until/return with
                  both ` and ` and ` or `): the coverage gate is line-granular and cannot see an untaken
                  branch, an unrun loop body or an uncalled function on a one-line form
  kernel-java     name a Java-side global: getPlayer, getOnlinePlayers, getSpecificPlayer,
                  SandboxVars, getSandboxOptions, Events, Hook, CharacterStat, MoodleType,
                  CharacterTrait, ModData, getGameTime, getWorld, isServer, isClient,
                  sendServerCommand, sendClientCommand, print
Comments and strings are blanked first (kahlua_lint.strip). Stdlib only; read-only.
"""
import argparse, collections, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kahlua_lint import strip, lua_files

Finding = collections.namedtuple("Finding", "path line rule detail")

HOISTED_RX = re.compile(r"--\s*@hoisted\s+(.*)$")
RULES = [
    ("alloc", re.compile(r"\{"), "table constructor allocates per tick"),
    ("concat", re.compile(r"\.\."), "string concatenation allocates per tick"),
    ("pcall", re.compile(r"\b(?:x?pcall|error|assert)\s*\("), "protected call per tick (one @rimguard allowed per region)"),
    ("string", re.compile(r"\b(?:string\.\w+|tostring|tonumber|table\.\w+)\s*\("), "string or table library call per tick"),
    ("math", re.compile(r"\^|\bmath\.(?:exp|pow|log|sqrt)\s*\("), "exponential or power per tick: compute on the slow clock"),
    ("loop", re.compile(r"^\s*(?:for|while|repeat)\b"), "loop per tick"),
]
METHOD_CALL_RX = re.compile(r"([A-Za-z_]\w*):\w+\s*\(")
FAST_OPEN_RX = re.compile(r"^\s*--\s*@fastpath\b")
FAST_CLOSE_RX = re.compile(r"^\s*--\s*@endfastpath\b")
KERNEL_FUNC_RX = re.compile(r"^\s*function\s+(NutritionRevamp\.kernel|K)\.[\w.]+\s*\(")
ANY_FUNC_RX = re.compile(r"^\s*(?:local\s+)?function\b|=\s*function\s*\(")
JAVA_GLOBALS = ("getPlayer", "getOnlinePlayers", "getSpecificPlayer", "SandboxVars", "getSandboxOptions",
                "Events", "Hook", "CharacterStat", "MoodleType", "CharacterTrait", "ModData", "getGameTime",
                "getWorld", "isServer", "isClient", "sendServerCommand", "sendClientCommand", "print")
ONELINE_RX = re.compile(r"\b(?:then|else|do|repeat)\b\s*\S|^\s*function\b[^()]*\([^)]*\)\s*\S")
PICK_RX = re.compile(r"\band\b.+\bor\b")
COND_START_RX = re.compile(r"^\s*(?:if|elseif|while|until|return)\b")
JAVA_RX = re.compile(r"(?<![\w.])(?:%s)\b" % "|".join(JAVA_GLOBALS))


def lint_text(path, text):
    found, raw_lines = [], text.split("\n")
    lines = strip(text).split("\n")
    hoisted = set()
    for raw in raw_lines:
        m = HOISTED_RX.search(raw)
        if m:
            hoisted.update(w.strip() for w in m.group(1).split(",") if w.strip())
    in_region, region_start, rimguard_used = False, 0, False
    kernel = os.path.basename(path).startswith("NR_Kernel")
    for n, (line, raw) in enumerate(zip(lines, raw_lines), 1):
        if FAST_OPEN_RX.match(raw):
            if in_region:
                found.append(Finding(path, n, "region", "@fastpath inside an open region"))
            in_region, region_start, rimguard_used = True, n, False
            continue
        if FAST_CLOSE_RX.match(raw):
            if not in_region:
                found.append(Finding(path, n, "region", "@endfastpath with no open region"))
            in_region = False
            continue
        if in_region:
            for rule, rx, detail in RULES:
                if rx.search(line):
                    if rule == "pcall" and "@rimguard" in raw and not rimguard_used:
                        rimguard_used = True
                        continue
                    found.append(Finding(path, n, rule, detail))
            for m in METHOD_CALL_RX.finditer(line):
                if m.group(1) not in hoisted:
                    found.append(Finding(path, n, "unhoisted-call", f"method call on {m.group(1)!r}, not in @hoisted"))
        if kernel:
            if ANY_FUNC_RX.search(line) and not KERNEL_FUNC_RX.search(line):
                found.append(Finding(path, n, "kernel-shape", "a kernel function is `function NutritionRevamp.kernel.<path>(` or `function K.<path>(`"))
            if ONELINE_RX.search(line) or (PICK_RX.search(line) and not COND_START_RX.match(line)):
                found.append(Finding(path, n, "kernel-oneline", "kernel: one statement per line " + chr(8212) + " the coverage gate cannot see an untaken branch on a one-line form"))
            if JAVA_RX.search(line):
                found.append(Finding(path, n, "kernel-java", "the kernel never names a Java-side global"))
    if in_region:
        found.append(Finding(path, region_start, "region", "@fastpath never closed"))
    return found


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
