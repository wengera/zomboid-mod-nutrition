"""The tuning-dial registry tool (Plan 19 Task 2; spec docs/superpowers/specs/2026-10-21-dials-and-hedonics-design.md
Part A; ruling T1-1).

    python tools/dials.py list [--domain D] [--src S]   a table of every dial, filtered by domain or source token
    python tools/dials.py check                         every row valid; exit 1 on any finding (a section 3 gate)
    python tools/dials.py diff A [B]                    the dials changed between two commits (B: the working tree)
    python tools/dials.py set ID VALUE                  edit one row's value in place, then print what to regenerate

The registry is mod/NutritionRevamp/common/media/lua/shared/NR_Data_Dials.lua (NR.data.dials), one row a line:
D['<domain>.<path>'] = { value = ..., unit = '...', min = ..., max = ..., src = '...', note = '...' } -- provenance.
It is read through lupa (the values as Lua evaluates them) and by line (each row's value as written, its line number
and its trailing provenance comment).

check finds:
- a row line the file does not evaluate to, a row the regex does not see, or one id on two lines;
- a field outside value, unit, min, max, src, note, opt, int, param, fit, same, fixed;
- a missing unit, src or note; a value that is not a number, a boolean or a table of them; a number (or a table's
  number) outside [min, max], a min over its max, or a boolean row with a range;
- a src token that is not S<4 digits>, #<4 digits>, game choice, vanilla, fitted or inference; an S id absent from
  docs/reference/science.tsv or a # id absent from docs/reference/claims.tsv; a vanilla src naming no # row;
- a same row that names an unknown dial, carries a value, range, option, int, param or fixed of its own, sits in a
  cycle, or whose unit differs from the unit of the dial it resolves to (the two are one dial); a same on an opt row
  K.dials.apply writes (a param row's option writes no field: its links are one dial for a registry tune, and the option moves only what its domain's parameter read applies it to);
- an opt row whose value is not a number or boolean, which is fixed or same, or whose option in
  42.21/media/sandbox-options.txt is missing or disagrees with the row's default (as written: written(), three decimal
  places), min, max or int; an opt row K.dials.apply writes whose value is not exact at three places;
- int without opt, param that is not true or has no opt or no numeric value, a non-integer int row, an empty fit, a
  fixed row that is not min == max == value;
- a chain of ASCENDING (knots a reader divides by the gaps of, a ladder read in order; a descending ladder listed reversed) whose values do not ascend;
- an orphan (an id no K.dials.get in the mod's Lua names) and a K.dials.get naming no row; an opt row K.dials.apply
  writes that does not resolve as K.<id> = K.dials.get(...).
The option file itself is generated from the opt rows (tools/sandbox_options.py --check).
Stdlib and lupa only; read-only except set.
"""
import argparse
import csv
import glob
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_REL = "mod/NutritionRevamp/common/media/lua/shared/NR_Data_Dials.lua"
LUA_REL = "mod/NutritionRevamp/common/media/lua"
SANDBOX_REL = "mod/NutritionRevamp/42.21/media/sandbox-options.txt"
SCIENCE_REL = "docs/reference/science.tsv"
CLAIMS_REL = "docs/reference/claims.tsv"

FIELDS = ("value", "unit", "min", "max", "src", "note", "opt", "int", "param", "fit", "same", "fixed")
WRITTEN_PLACES = 1000                                 # the option file's three decimal places (K.dials.WRITTEN_PLACES)
CLASSES = ("game choice", "vanilla", "fitted", "inference")
# the chains that must ascend: x knots K.interp divides by the gaps of, and a ladder read in order
ASCENDING = (("strength.DEFAULTS.fp_knots.1.1", "strength.DEFAULTS.fp_knots.2.1", "strength.DEFAULTS.fp_knots.3.1",
              "strength.DEFAULTS.fp_knots.4.1"),
             ("fluids.THIRST_KNOTS.2.1", "fluids.THIRST_KNOTS.3.1", "fluids.THIRST_KNOTS.4.1",   # K.fluids.tVol
              "fluids.THIRST_KNOTS.5.1", "fluids.THIRST_KNOTS.6.1"),                             # (5.1 is drain.DEHYD_ONSET)
             ("drain.STARVE_PHASE_H.1", "drain.STARVE_PHASE_H.2", "drain.STARVE_PHASE_H.3"),     # K.drain.starvePhase
             ("hungerCurve.X.2", "hungerCurve.X.3", "hungerCurve.X.4", "hungerCurve.X.5", "hungerCurve.X.6"),  # K.hungerCurve.map divides by X gaps
             ("effects.ALC_EDGES.1", "effects.ALC_EDGES.2"),                                                   # K.effects.atOrAbove
             ("effects.DEBT_EDGES.1", "effects.DEBT_EDGES.2"),
             tuple("effects.DEHYD_EDGES.%d" % i for i in range(1, 9)),
             ("effects.BG_EDGES.3", "effects.BG_EDGES.2", "effects.BG_EDGES.1"),                               # K.effects.below: descending
             ("effects.EA_EDGES.3", "effects.EA_EDGES.2", "effects.EA_EDGES.1"),
             ("energy.LOAD_FLOOR.1.1", "energy.LOAD_FLOOR.2.1", "energy.LOAD_FLOOR.3.1"),                      # loadFloor: thresholds ascend
             ("fluids.HYPONAT.3", "fluids.HYPONAT.2", "fluids.HYPONAT.1"),                                     # hyponatGrade: descending
             ("nutrients.LADDER.3", "nutrients.LADDER.2", "nutrients.LADDER.1"),                               # K.nutrients.grade: descending
             ("traits.THIN_CUTS.3", "traits.THIN_CUTS.2", "traits.THIN_CUTS.1"),                               # K.traits.held, down
             ("traits.FAT_CUTS.1.1", "traits.FAT_CUTS.1.2"), ("traits.FAT_CUTS.2.1", "traits.FAT_CUTS.2.2"),   # K.traits.held, up, by sex
             ("view.STIMULANT_AT.1", "view.STIMULANT_AT.2", "view.STIMULANT_AT.3", "view.STIMULANT_AT.4"),     # K.view.rung
             ("view.SLEEP_AT.1", "view.SLEEP_AT.2", "view.SLEEP_AT.3", "view.SLEEP_AT.4"),
             ("view.OVERFULL_AT.1", "view.OVERFULL_AT.2", "view.OVERFULL_AT.3"),
             ("view.FAT_CUTS_MALE.1", "view.FAT_CUTS_MALE.2", "view.FAT_CUTS_MALE.3", "view.FAT_CUTS_MALE.4"),  # K.view.heldRung
             ("view.FAT_CUTS_FEMALE.1", "view.FAT_CUTS_FEMALE.2", "view.FAT_CUTS_FEMALE.3", "view.FAT_CUTS_FEMALE.4"))
SCIENCE_ID = re.compile(r"^S\d{4}$")
CLAIM_ID = re.compile(r"^#\d{4}$")
ROW_RX = re.compile(r"^D\['([^']+)'\] = \{")
GET_RX = re.compile(r"""K\.dials\.get\(\s*["']([^"']+)["']\s*\)""")
# the domains whose dials reach a generated file (NR_Data_Fills.lua replays satiety, stomach, hungerCurve and view)
FILLS_DOMAINS = ("satiety", "stomach", "hungerCurve", "view")


def _path(root, rel):
    return os.path.join(root, *rel.split("/"))


def _read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read().replace("\r\n", "\n")


# --- reading the registry ---------------------------------------------------------------------------------------

def _py(v):
    """A Lua value as Python: a table whose keys are 1..n is a list, any other table a dict."""
    import lupa.lua51 as lua51
    if lua51.lua_type(v) != "table":
        return v
    d = {k: _py(x) for k, x in v.items()}
    if d and all(isinstance(k, int) and not isinstance(k, bool) for k in d) and sorted(d) == list(range(1, len(d) + 1)):
        return [d[i] for i in range(1, len(d) + 1)]
    return d


def load_rows(text):
    """The registry text evaluated: {id: row dict}. Raises a lupa error on text Lua cannot run."""
    import lupa.lua51 as lua51
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute("NutritionRevamp = {}")
    rt.eval("function(src) return assert(loadstring(src, '@NR_Data_Dials.lua')) end")(text)()
    dials = rt.globals().NutritionRevamp.data.dials
    return {k: _py(v) for k, v in dials.items()}


def row_lines(text):
    """{id: [line number, ...]} of every row line (D['id'] = { at column 0)."""
    out = {}
    for n, line in enumerate(text.split("\n"), 1):
        m = ROW_RX.match(line)
        if m:
            out.setdefault(m.group(1), []).append(n)
    return out


_VALUES = {}                                          # registry text -> its values (one Lua evaluation per text)


def values(text=None):
    """{id: value} of every dial as K.dials.get returns it, a same row resolved to the value of the dial it names: the
    tools that model a kernel in Python (fit_hunger_curve) read the registry here instead of keeping their own copy.
    A fresh dict each call; the registry is evaluated once per text."""
    if text is None:
        text = _read(_path(REPO, REGISTRY_REL))
    if text not in _VALUES:
        rows = load_rows(text)
        out = {}
        for dial_id in rows:
            end, why = _resolve(rows, dial_id)
            if why:
                raise ValueError("%s: same %s" % (dial_id, why))
            out[dial_id] = rows[end]["value"]
        _VALUES[text] = out
    return dict(_VALUES[text])


_LINKED = {}                                          # registry text -> {id: [the ids that are one dial with it]}


def linked(dial_id, text=None):
    """The ids that are one dial with dial_id: the id its same chain ends at first, then every other id whose chain
    ends there, sorted; [dial_id] alone for an id with no row. A tool that patches kernel fields (fit_gut_satiety's
    _apply) writes each of them, so a fit of satiety.MEAL_REQ moves hungerCurve.FED_M with it and never the registry."""
    if text is None:
        text = _read(_path(REPO, REGISTRY_REL))
    if text not in _LINKED:
        rows = load_rows(text)
        groups = {}
        for i in rows:
            end, why = _resolve(rows, i)
            if why:
                raise ValueError("%s: same %s" % (i, why))
            groups.setdefault(end, []).append(i)
        index = {}
        for end, ids in groups.items():
            group = [end] + sorted(i for i in ids if i != end)
            for i in group:
                index[i] = group
        _LINKED[text] = index
    return list(_LINKED[text].get(dial_id, [dial_id]))


def source_line(dial_id, text=None):
    """The registry line of dial_id, exactly as written (the provenance helper the kernel tests read instead of a
    kernel constant's line). Raises KeyError for an id with no line."""
    if text is None:
        text = _read(_path(REPO, REGISTRY_REL))
    lines = text.split("\n")
    hits = row_lines(text).get(dial_id)
    if not hits:
        raise KeyError(dial_id)
    return lines[hits[0] - 1]


def provenance(dial_id, text=None):
    """The trailing comment of dial_id's line: the long provenance, verbatim from the kernel line it replaced."""
    line = source_line(dial_id, text)
    i = line.find(" } -- ")
    return line[i + len(" } -- "):] if i >= 0 else ""


def _value_span(line):
    """(start, end) of the value expression on a row line (`value = <expr>` up to the next top-level comma), or None."""
    m = re.search(r"\{ value = ", line)
    if not m:
        return None
    i, depth, quote = m.end(), 0, None
    start = i
    while i < len(line):
        c = line[i]
        if quote:
            if c == quote:
                quote = None
        elif c in "'\"":
            quote = c
        elif c in "{([":
            depth += 1
        elif c in "})]":
            if depth == 0:
                break
            depth -= 1
        elif c == "," and depth == 0:
            break
        i += 1
    return start, i


def value_text(line):
    span = _value_span(line)
    return line[span[0]:span[1]].strip() if span else ""


# --- the sources ------------------------------------------------------------------------------------------------

def _ids(path, col="id"):
    csv.field_size_limit(10 ** 9)
    with open(path, encoding="utf-8", newline="") as fh:
        return {r[col] for r in csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)}


def src_tokens(src):
    """The tokens of a src cell: each class phrase, then each remaining whitespace-separated word."""
    rest, out = " %s " % src, []
    for c in CLASSES:
        if " %s " % c in rest:
            out.append(c)
            rest = rest.replace(" %s " % c, " ")
    return out + rest.split()


def sandbox_options(text):
    """{name: {field: text}} of every `option NR.<name> { ... }` block."""
    out = {}
    for m in re.finditer(r"option\s+NR\.(\w+)\s*\{([^}]*)\}", text):
        fields = dict(re.findall(r"(\w+)\s*=\s*([^,\n]+)", m.group(2)))
        out[m.group(1)] = {k: v.strip() for k, v in fields.items()}
    return out


# --- check ------------------------------------------------------------------------------------------------------

def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def written(v):
    """A number as the option file declares it: rounded half up to three decimal places, as K.dials.written computes it
    (the same double operations, so the two agree bit for bit)."""
    import math
    return math.floor(v * WRITTEN_PLACES + 0.5) / WRITTEN_PLACES


def _leaves(v):
    if isinstance(v, list):
        for x in v:
            yield from _leaves(x)
    elif isinstance(v, dict):
        for x in v.values():
            yield from _leaves(x)
    else:
        yield v


def _resolve(rows, dial_id):
    """(the id a same chain ends at, None) or (None, the reason it does not end)."""
    seen = [dial_id]
    cur = dial_id
    while "same" in rows.get(cur, {}):
        cur = rows[cur]["same"]
        if cur not in rows:
            return None, "names an unknown dial %s" % cur
        if cur in seen:
            return None, "sits in a cycle %s" % " -> ".join(seen + [cur])
        seen.append(cur)
    return cur, None


def _check_value(dial_id, row):
    out = []
    v, lo, hi = row.get("value"), row.get("min"), row.get("max")
    if isinstance(v, bool):
        if lo is not None or hi is not None:
            out.append("%s: a boolean dial carries no range" % dial_id)
        return out
    if v is None:
        return ["%s: no value" % dial_id]
    if not (_num(v) or isinstance(v, (list, dict))):
        return ["%s: value %r is not a number, a boolean or a table" % (dial_id, v)]
    nums = [x for x in _leaves(v) if _num(x)]
    odd = [x for x in _leaves(v) if not _num(x) and not isinstance(x, bool)]
    if odd:
        out.append("%s: a table value holds %r, not a number or boolean" % (dial_id, odd[0]))
    if not nums:
        return out
    if not (_num(lo) and _num(hi)) or any(x != x or x in (float("inf"), float("-inf")) for x in (lo, hi)):
        return out + ["%s: no finite numeric min and max" % dial_id]
    if lo > hi:
        return out + ["%s: min %r over max %r" % (dial_id, lo, hi)]
    for x in nums:
        if not lo <= x <= hi:
            out.append("%s: value %r outside [%r, %r]" % (dial_id, x, lo, hi))
    if row.get("int") is True and any(x != int(x) for x in nums + [lo, hi]):
        out.append("%s: an int dial holds a non-integer" % dial_id)
    if row.get("fixed") is True and _num(v) and not lo == hi == v:
        out.append("%s: a fixed dial must read min == max == value" % dial_id)
    return out


def _check_src(dial_id, src, science, claims):
    if not isinstance(src, str) or not src.strip():
        return ["%s: no src" % dial_id]
    out, toks = [], src_tokens(src)
    for t in toks:
        if t in CLASSES:
            continue
        if SCIENCE_ID.match(t):
            if t not in science:
                out.append("%s: src %s is not a row of %s" % (dial_id, t, SCIENCE_REL))
        elif CLAIM_ID.match(t):
            if t not in claims:
                out.append("%s: src %s is not a row of %s" % (dial_id, t, CLAIMS_REL))
        else:
            out.append("%s: src token %r is not an S id, a # id or one of %s" % (dial_id, t, ", ".join(CLASSES)))
    if "vanilla" in toks and not any(CLAIM_ID.match(t) for t in toks):
        out.append("%s: a vanilla src names no # row" % dial_id)
    return out


def _check_opt(dial_id, row, options):
    out, opt = [], row["opt"]
    v = row.get("value")
    if not (_num(v) or isinstance(v, bool)):
        out.append("%s: a sandbox-backed dial must hold a number or a boolean" % dial_id)
    if row.get("fixed") is True:
        out.append("%s: a fixed dial is never sandbox-backed" % dial_id)
    o = options.get(opt)
    if o is None:
        return out + ["%s: option NR.%s is not in %s" % (dial_id, opt, SANDBOX_REL)]
    kind = o.get("type", "")
    if kind == "boolean":
        if o.get("default") != ("true" if v is True else "false"):
            out.append("%s: option NR.%s default %s differs from the value %r" % (dial_id, opt, o.get("default"), v))
        return out
    want_int = kind in ("integer", "enum")
    if want_int != (row.get("int") is True):
        out.append("%s: option NR.%s is %s, so int must be %s" % (dial_id, opt, kind, str(want_int).lower()))
    lo, hi = (1.0, float(o.get("numValues", "nan"))) if kind == "enum" else (float(o.get("min", "nan")), float(o.get("max", "nan")))
    if _num(v) and row.get("param") is not True and written(v) != v:
        out.append("%s: K.dials.apply writes the option's read into the field, so the value must be exact at the option "
                   "file's three decimal places (or the row is param)" % dial_id)
    default = written(v) if _num(v) else v
    for name, theirs, ours in (("default", float(o.get("default", "nan")), default), ("min", lo, row.get("min")), ("max", hi, row.get("max"))):
        if not (_num(ours) and theirs == ours):
            out.append("%s: option NR.%s %s %r differs from the row's %r" % (dial_id, opt, name, theirs, ours))
    return out


def check_rows(rows, science, claims, options):
    out = []
    for dial_id in sorted(rows):
        row = rows[dial_id]
        extra = sorted(set(row) - set(FIELDS))
        if extra:
            out.append("%s: fields outside the row shape: %s" % (dial_id, ", ".join(extra)))
        if "." not in dial_id:
            out.append("%s: an id is <domain>.<path>" % dial_id)
        for f in ("unit", "note"):
            if not (isinstance(row.get(f), str) and row[f].strip()):
                out.append("%s: no %s" % (dial_id, f))
        out += _check_src(dial_id, row.get("src"), science, claims)
        if "same" in row:
            own = [f for f in ("value", "min", "max", "opt", "int", "param", "fixed") if f in row]
            if own:
                out.append("%s: a same row carries no %s of its own" % (dial_id, ", ".join(own)))
            end, why = _resolve(rows, dial_id)
            if why:
                out.append("%s: same %s" % (dial_id, why))
            elif rows[end].get("unit") != row.get("unit"):
                out.append("%s: unit %r differs from %s's %r" % (dial_id, row.get("unit"), end, rows[end].get("unit")))
            if not why and "opt" in rows[end] and rows[end].get("param") is not True:
                out.append("%s: same %s, a sandbox-backed dial: K.dials.apply writes only K.%s, so this field would "
                           "not follow the option" % (dial_id, end, end))
            continue
        out += _check_value(dial_id, row)
        if "fixed" in row and row["fixed"] is not True:
            out.append("%s: fixed is true or absent" % dial_id)
        if "int" in row and "opt" not in row:
            out.append("%s: int describes an option, and the row has none" % dial_id)
        if "param" in row and (row["param"] is not True or "opt" not in row or not _num(row.get("value"))):
            out.append("%s: param is true on a numeric row with an option, or absent" % dial_id)
        if "fit" in row and not (isinstance(row["fit"], str) and row["fit"].strip()):
            out.append("%s: an empty fit" % dial_id)
        if "opt" in row:
            out += _check_opt(dial_id, row, options)
    return out


LHS_RX = re.compile(r"^\s*([A-Za-z_][\w.]*)\s*=\s*K\.dials\.get\(")


def mod_gets(root):
    """{id: [(path:line, the left-hand side or None), ...]} of every K.dials.get in the mod's Lua, the registry aside."""
    out = {}
    for path in sorted(glob.glob(os.path.join(_path(root, LUA_REL), "**", "*.lua"), recursive=True)):
        if os.path.basename(path) == "NR_Data_Dials.lua":
            continue
        for n, line in enumerate(_read(path).split("\n"), 1):
            code = line.split("--")[0]
            lhs = LHS_RX.match(code)
            for m in GET_RX.finditer(code):
                out.setdefault(m.group(1), []).append(("%s:%d" % (os.path.basename(path), n), lhs.group(1) if lhs else None))
    return out


def _order(vals):
    out = []
    for chain in ASCENDING:
        missing = [i for i in chain if i not in vals]
        if len(missing) == len(chain):                         # a registry without the chain (a scratch tree)
            continue
        if missing:                                            # a renamed knot would switch the rule off unseen
            out.append("%s: the knot chain is incomplete: missing %s" % (chain[-1], ", ".join(missing)))
            continue
        xs = [vals[i] for i in chain]
        if any(b <= a for a, b in zip(xs, xs[1:])):
            out.append("%s: the chain must ascend (an interpolation divides by its gaps, a ladder reads it in order): %r"
                       % (chain[-1], xs))
    return out


def check(root=REPO, text=None):
    """Every finding over the registry at root (or text in its place). An empty list is green."""
    if text is None:
        text = _read(_path(root, REGISTRY_REL))
    try:
        rows = load_rows(text)
    except Exception as e:                                   # a lupa syntax or runtime error
        return ["%s: does not evaluate: %s" % (REGISTRY_REL, e)]
    out = []
    lines = row_lines(text)
    for dial_id, ns in sorted(lines.items()):
        if len(ns) > 1:
            out.append("%s: on more than one line (%s)" % (dial_id, ", ".join(map(str, ns))))
    for dial_id in sorted(set(rows) - set(lines)):
        out.append("%s: a row with no D['id'] = { line of its own" % dial_id)
    rows_text = text.split("\n")
    for dial_id, ns in sorted(lines.items()):
        code = rows_text[ns[0] - 1].split(" -- ")[0]
        if code.count("{") != code.count("}"):
            out.append("%s: a row spans more than its one line" % dial_id)
    science = _ids(_path(root, SCIENCE_REL))
    claims = _ids(_path(root, CLAIMS_REL))
    options = sandbox_options(_read(_path(root, SANDBOX_REL)))
    out += check_rows(rows, science, claims, options)
    try:
        out += _order(values(text))
    except ValueError:                                       # a same cycle or unknown name: check_rows names it
        pass
    gets = mod_gets(root)
    for dial_id in sorted(set(rows) - set(gets)):
        out.append("%s: an orphan: no K.dials.get in the mod names it" % dial_id)
    for dial_id in sorted(set(gets) - set(rows)):
        out.append("%s: K.dials.get at %s names no row" % (dial_id, ", ".join(w for w, _ in gets[dial_id])))
    for dial_id in sorted(i for i in rows if "opt" in rows[i] and rows[i].get("param") is not True and i in gets):
        if dial_id.startswith("core."):
            out.append("%s: a core dial is K's top level (K.%s), which K.dials.bind cannot write; give K.dials.bind a core "
                       "mapping before it takes an option" % (dial_id, dial_id[len("core."):]))
            continue
        if any(lhs != "K." + dial_id for _, lhs in gets[dial_id]):
            out.append("%s: a sandbox-backed dial must resolve as K.%s = K.dials.get(...), the field K.dials.apply writes"
                       % (dial_id, dial_id))
    return out


# --- list, diff, set --------------------------------------------------------------------------------------------

def table(text, domain=None, src=None):
    """The list's rows: (id, value as written, unit, min, max, src, flags)."""
    rows, lines = load_rows(text), text.split("\n")
    out = []
    for dial_id, ns in sorted(row_lines(text).items()):
        row = rows.get(dial_id, {})
        if domain and dial_id.split(".")[0] != domain:
            continue
        if src and src not in src_tokens(row.get("src", "")):
            continue
        flags = " ".join("%s=%s" % (f, row[f]) for f in ("opt", "fit", "same") if f in row)
        if row.get("fixed") is True:
            flags = (flags + " fixed").strip()
        out.append((dial_id, value_text(lines[ns[0] - 1]) or "-", row.get("unit", ""), _fmt(row.get("min")),
                    _fmt(row.get("max")), row.get("src", ""), flags))
    return out


def _fmt(v):
    return "" if v is None else repr(v)


def _show(root, rev):
    """The registry text at rev (a commit), or '' where it does not exist."""
    p = subprocess.run(["git", "-C", root, "show", "%s:%s" % (rev, REGISTRY_REL)], capture_output=True)
    return p.stdout.decode("utf-8").replace("\r\n", "\n") if p.returncode == 0 else ""


def _snapshot(text):
    if not text:
        return {}
    rows, lines = load_rows(text), text.split("\n")
    out = {}
    for dial_id, ns in row_lines(text).items():
        row = dict(rows.get(dial_id, {}))
        if "value" in row:
            row["value"] = value_text(lines[ns[0] - 1])
        out[dial_id] = row
    return out


def diff(a_text, b_text):
    """The dial changes from a_text to b_text: ['+ id', '- id', '~ id field: old -> new', ...]."""
    a, b = _snapshot(a_text), _snapshot(b_text)
    out = ["+ %s" % i for i in sorted(set(b) - set(a))] + ["- %s" % i for i in sorted(set(a) - set(b))]
    for i in sorted(set(a) & set(b)):
        for f in FIELDS:
            if a[i].get(f) != b[i].get(f):
                out.append("~ %s %s: %r -> %r" % (i, f, a[i].get(f), b[i].get(f)))
    return out


def set_value(text, dial_id, new, root=REPO):
    """(the new registry text, notes) with dial_id's value replaced by the Lua literal new, the line's format kept.
    Raises ValueError for an unknown, same or fixed dial, a value that does not evaluate, or one the check refuses."""
    lines = text.split("\n")
    ns = row_lines(text).get(dial_id)
    if not ns:
        raise ValueError("no dial %s" % dial_id)
    rows = load_rows(text)
    row = rows[dial_id]
    if "same" in row:
        raise ValueError("%s resolves to %s: set that dial" % (dial_id, row["same"]))
    if row.get("fixed") is True:
        raise ValueError("%s is fixed: a value read off the game is never tuned" % dial_id)
    probe = new.strip()
    if "--" in probe or "\n" in probe or _value_span("{ value = " + probe + "}")[1] != len("{ value = ") + len(probe):
        raise ValueError("%s: %r is not one Lua value" % (dial_id, new))
    line = lines[ns[0] - 1]
    start, end = _value_span(line)
    lines[ns[0] - 1] = line[:start] + new.strip() + line[end:]
    out = "\n".join(lines)
    try:
        new_rows = load_rows(out)
    except Exception as e:
        raise ValueError("%s: %s does not evaluate: %s" % (dial_id, new, e))
    if "opt" in row:
        import sandbox_options as option_file      # the option file as --write will render it from the new registry
        sandbox = sandbox_options(option_file.render(out))
    else:
        sandbox = sandbox_options(_read(_path(root, SANDBOX_REL)))
    found = [f for f in check_rows({dial_id: new_rows[dial_id]}, _ids(_path(root, SCIENCE_REL)),
                                   _ids(_path(root, CLAIMS_REL)), sandbox)]
    found += _order(values(out))
    if found:
        raise ValueError("; ".join(found))
    return out, regenerate_notes(dial_id, row)


def regenerate_notes(dial_id, row):
    notes = []
    if "fit" in row:
        notes.append("%s is owned by the fit %s: re-run it, or say why the hand value stands" % (dial_id, row["fit"]))
    if "opt" in row:
        notes.append("python tools/sandbox_options.py --write   (%s is NR.%s's default in %s)" % (dial_id, row["opt"], SANDBOX_REL))
    if dial_id.split(".")[0] in FILLS_DOMAINS:
        notes.append("python tools/food_fills.py --write")
    notes.append("python tools/mod_guide_data.py --write")
    notes.append("python -m pytest testing/tests/kernel/test_golden_trace.py -q   (a moved trace re-records under a named cause, CLAUDE.md section 6)")
    notes.append("python tools/dials.py check")
    return notes


def main(argv=None):
    ap = argparse.ArgumentParser(description="The tuning-dial registry: list, check, diff, set.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list")
    p.add_argument("--domain")
    p.add_argument("--src", help="a src token: an S or # id, or a class such as 'game choice'")
    sub.add_parser("check")
    p = sub.add_parser("diff")
    p.add_argument("a")
    p.add_argument("b", nargs="?", help="a commit; the working tree when absent")
    p = sub.add_parser("set")
    p.add_argument("id")
    p.add_argument("value", help="a Lua literal: a number, true or false, or a table")
    ap.add_argument("--root", default=REPO, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    root = args.root
    if args.cmd == "check":
        found = check(root)
        for f in found:
            print(f)
        print("%d findings" % len(found))
        return 1 if found else 0
    if args.cmd == "list":
        rows = table(_read(_path(root, REGISTRY_REL)), args.domain, args.src)
        head = ("id", "value", "unit", "min", "max", "src", "flags")
        w = [max(len(str(r[i])) for r in rows + [head]) for i in range(len(head))]
        for r in [head] + rows:
            print("  ".join(str(c).ljust(w[i]) for i, c in enumerate(r)).rstrip())
        print("%d dials" % len(rows))
        return 0
    if args.cmd == "diff":
        b = _show(root, args.b) if args.b else _read(_path(root, REGISTRY_REL))
        for line in diff(_show(root, args.a), b):
            print(line)
        return 0
    path = _path(root, REGISTRY_REL)
    try:
        out, notes = set_value(_read(path), args.id, args.value, root)
    except ValueError as e:
        print("refused: %s" % e)
        return 1
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    print("set %s = %s" % (args.id, args.value))
    for n in notes:
        print("  then: %s" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
