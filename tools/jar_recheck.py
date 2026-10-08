#!/usr/bin/env python3
"""Re-read register pointers on the installed build (Plan 11a Task R, the 42.21 re-baseline).

For every `jar:` pointer of the form `Class[$Inner].method[(params)[ret]] @a[-@b] La[-Lb]` (several spans allowed)
or `Class.method @La-Lb` (lines only), it dumps the method with the jar toolchain's disassembler
(C:\\Users\\Angus\\pz-b42\\tools\\pzdis.py, what pz.sh runs; read-only) and reports whether each cited offset is
still an instruction whose source line is the cited line. For every `lua:` pointer `<path under media/>:<line>
"anchor"` it reports whether that line of the install's file still carries the anchor. It writes one TSV line per
pointer with a status, a proposed re-anchored pointer when every offset or the anchor is still there but the lines
moved, and the instructions at the cited offsets, so a reader can judge the claim. It never edits the register:
whether a claim holds is the reader's verdict.

Statuses: same, shifted, offsets-missing, lines-missing, no-method, no-class, ambiguous-class, unparsed (jar);
same, anchor-moved, anchor-missing, anchor-ambiguous, no-file, unparsed (lua); no-row.

    python tools/jar_recheck.py --ids <file of #dddd ids> --out <report.tsv>
                                [--register TSV] [--jar JAR] [--pzdis PZDIS] [--media DIR]
"""
import argparse
import os
import re
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claimslib as cl  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO, "docs", "reference", "claims.tsv")
JAR = r"D:\SteamLibrary\steamapps\common\ProjectZomboid\projectzomboid.jar"
MEDIA = r"D:\SteamLibrary\steamapps\common\ProjectZomboid\media"
PZDIS = r"C:\Users\Angus\pz-b42\tools\pzdis.py"
HEADER = ("id", "form", "pointer", "status", "proposed", "span")

JAR_PTR_RX = re.compile(r"^(?P<cls>[A-Za-z_][\w$]*)\.(?P<meth>[\w<>$]+)(?P<desc>\([^)]*\)\S*)?\s+(?P<spans>@.*)$")
SPAN_RX = re.compile(r"@(?P<o1>\d+)(?:\s*[-\u2013]\s*@(?P<o2>\d+))?\s+L(?P<l1>\d+)(?:\s*[-\u2013]\s*L?(?P<l2>\d+))?")
LINES_RX = re.compile(r"^@L(?P<l1>\d+)(?:\s*[-\u2013]\s*L?(?P<l2>\d+))?$")
HEAD_RX = re.compile(r"^### (?P<name>[^(\s]+)(?P<desc>\(.*)$")
INSN_RX = re.compile(r"^\s+(?P<off>\d+)\s+(?:L(?P<line>\d+)\s+)?(?P<op>\S+)")
LUA_RX = re.compile(r'^(?P<path>[^\s"]+):(?P<l1>\d+)(?:[-\u2013](?P<l2>\d+))?\s+"(?P<anchor>[^"]+)"$')
PRIM = {"Z": "boolean", "B": "byte", "C": "char", "S": "short", "I": "int", "J": "long", "F": "float",
        "D": "double", "V": "void"}


def parse_jar(text):
    """A jar pointer's payload -> {text, cls, meth, desc, spans: [(o1, o2, l1, l2)], lines: (l1, l2) | None},
    or None for a form this tool does not read (a member list, a bare signature, a dotted class path)."""
    text = text.strip()
    m = JAR_PTR_RX.match(text)
    if m is None:
        return None
    rest = m.group("spans").strip()
    out = {"text": text, "cls": m.group("cls"), "meth": m.group("meth"), "desc": m.group("desc"),
           "spans": [], "lines": None}
    lm = LINES_RX.match(rest)
    if lm is not None:
        l1 = int(lm.group("l1"))
        out["lines"] = (l1, int(lm.group("l2") or l1))
        return out
    for sm in SPAN_RX.finditer(rest):
        out["spans"].append((int(sm.group("o1")), int(sm.group("o2")) if sm.group("o2") else None,
                             int(sm.group("l1")), int(sm.group("l2")) if sm.group("l2") else None))
    if not out["spans"] or SPAN_RX.sub("", rest).strip(" ,;"):
        return None
    return out


def parse_dump(text):
    """The disassembler's dump -> [(desc, {offset: line}, {offset: instruction text})], one per overload; each
    offset maps to the source line in force at it (the line table carried forward)."""
    out = []
    offs = insn = None
    line = None
    for raw in text.splitlines():
        h = HEAD_RX.match(raw)
        if h is not None:
            offs, insn, line = {}, {}, None
            out.append((h.group("desc"), offs, insn))
            continue
        if offs is None:
            continue
        i = INSN_RX.match(raw)
        if i is not None:
            if i.group("line"):
                line = int(i.group("line"))
            offs[int(i.group("off"))] = line
            insn[int(i.group("off"))] = raw.strip()
    return out


def simple_params(desc):
    """'(Lzombie/inventory/InventoryItem;FZ)Z' -> ['InventoryItem', 'float', 'boolean']."""
    inner = desc[1:desc.index(")")]
    out, i = [], 0
    while i < len(inner):
        dims = 0
        while inner[i] == "[":
            dims += 1
            i += 1
        if inner[i] == "L":
            j = inner.index(";", i)
            name = inner[i + 1:j].rsplit("/", 1)[-1]
            i = j + 1
        else:
            name = PRIM[inner[i]]
            i += 1
        out.append(name + "[]" * dims)
    return out


def desc_matches(cited, actual):
    """A cited `(...)` names an overload by its raw descriptor's prefix or by its simple parameter names."""
    if cited is None:
        return True
    if actual.startswith(cited):
        return True
    names = [p.strip() for p in cited[1:cited.index(")")].split(",") if p.strip()]
    return names == simple_params(actual)


def reanchor(text, offs):
    """The pointer text with each span's L numbers replaced by the lines now at its offsets."""
    def fix(sm):
        s, base = sm.group(0), sm.start(0)
        n1 = offs[int(sm.group("o1"))]
        head = s[:sm.start("l1") - base] + str(n1)
        if sm.group("l2") is None:
            return head + s[sm.end("l1") - base:]
        n2 = offs[int(sm.group("o2"))] if sm.group("o2") else n1
        return head + s[sm.end("l1") - base:sm.start("l2") - base] + str(n2) + s[sm.end("l2") - base:]
    return SPAN_RX.sub(fix, text)


def check_jar(ptr, overloads):
    """(status, proposed pointer or None) for one parsed jar pointer against the method's overloads."""
    cands = [(d, offs) for d, offs, _i in overloads if desc_matches(ptr["desc"], d)]
    if not cands:
        return "no-method", None
    if ptr["lines"] is not None:
        l1, l2 = ptr["lines"]
        for _d, offs in cands:
            have = set(v for v in offs.values() if v is not None)
            if l1 in have and l2 in have:
                return "same", None
        return "lines-missing", None
    best = None
    for _d, offs in cands:
        if not all(o in offs for o1, o2, _a, _b in ptr["spans"] for o in (o1, o2) if o is not None):
            continue
        if all(offs[o1] == l1 and (o2 is None or offs[o2] == (l2 if l2 is not None else l1))
               for o1, o2, l1, l2 in ptr["spans"]):
            return "same", None
        if best is None:
            best = offs
    if best is None:
        return "offsets-missing", None
    return "shifted", reanchor(ptr["text"], best)


def span_text(ptr, overloads):
    """The instructions at the cited offsets in the first overload that holds them all, for the reader."""
    for d, _offs, insn in overloads:
        if desc_matches(ptr["desc"], d) and all(o1 in insn for o1, _o2, _a, _b in ptr["spans"]):
            parts = []
            for o1, o2, _a, _b in ptr["spans"]:
                parts.append(insn[o1])
                if o2 is not None and o2 in insn:
                    parts.append(insn[o2])
            return " | ".join(parts)
    return ""


def check_lua(text, media):
    """(status, proposed pointer or None) for one `lua:` payload against the install's media folder."""
    m = LUA_RX.match(text.strip())
    if m is None:
        return "unparsed", None
    path = os.path.join(media, *m.group("path").split("/"))
    if not os.path.exists(path):
        return "no-file", None
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    n, anchor = int(m.group("l1")), m.group("anchor")
    if 1 <= n <= len(lines) and anchor in lines[n - 1]:
        return "same", None
    hits = [k + 1 for k, l in enumerate(lines) if anchor in l]
    if not hits:
        return "anchor-missing", None
    if len(hits) > 1:
        return "anchor-ambiguous", None
    span = str(hits[0])
    if m.group("l2"):
        span += "-%d" % (int(m.group("l2")) + hits[0] - n)
    return "anchor-moved", '%s:%s "%s"' % (m.group("path"), span, anchor)


def class_index(jar):
    """{short class name: [internal names]} over every class in the jar."""
    idx = {}
    with zipfile.ZipFile(jar) as z:
        for name in z.namelist():
            if name.endswith(".class"):
                idx.setdefault(name[:-6].rsplit("/", 1)[-1], []).append(name[:-6])
    return idx


def resolve(short, idx):
    names = idx.get(short, [])
    if len(names) > 1:
        game = [n for n in names if n.startswith("zombie/") or n.startswith("se/krka/")]
        if len(game) == 1:
            return game
    return names


def dump_text(internal, meth, jar=JAR, pzdis=PZDIS):
    res = subprocess.run([sys.executable, pzdis, jar, "dump", internal, meth], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    return res.stdout


def recheck(ids, rows, idx, dumper, media):
    by_id = {r["id"]: r for r in rows}
    out, cache = [], {}
    for cid in ids:
        r = by_id.get(cid)
        if r is None:
            out.append([cid, "", "", "no-row", "", ""])
            continue
        try:
            ptrs = cl.parse_pointers(r["pointer"])
        except ValueError:
            out.append([cid, "", r["pointer"], "unparsed", "", ""])
            continue
        for form, text in ptrs:
            if form == "lua":
                st, new = check_lua(text, media)
                out.append([cid, form, text, st, new or "", ""])
                continue
            if form != "jar":
                continue
            p = parse_jar(text)
            if p is None:
                out.append([cid, form, text, "unparsed", "", ""])
                continue
            names = resolve(p["cls"], idx)
            if not names:
                out.append([cid, form, text, "no-class", "", ""])
                continue
            if len(names) > 1:
                out.append([cid, form, text, "ambiguous-class", "", " ".join(names)])
                continue
            key = (names[0], p["meth"])
            if key not in cache:
                cache[key] = parse_dump(dumper(names[0], p["meth"]))
            st, new = check_jar(p, cache[key])
            out.append([cid, form, text, st, new or "", span_text(p, cache[key])])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ids", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--register", default=REGISTER)
    ap.add_argument("--jar", default=JAR)
    ap.add_argument("--pzdis", default=PZDIS)
    ap.add_argument("--media", default=MEDIA)
    a = ap.parse_args(argv)
    ids = []
    for line in open(a.ids, encoding="utf-8"):
        m = re.match(r"\s*(#\d{4})", line)
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    out = recheck(ids, cl.read_register(a.register), class_index(a.jar),
                  lambda c, m: dump_text(c, m, a.jar, a.pzdis), a.media)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(HEADER) + "\n")
        for row in out:
            f.write("\t".join(c.replace("\t", " ") for c in row) + "\n")
    counts = {}
    for row in out:
        counts[row[3]] = counts.get(row[3], 0) + 1
    print("jar_recheck: %d pointers over %d ids: %s" % (
        len(out), len(ids), ", ".join("%s %d" % kv for kv in sorted(counts.items()))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
