"""The data generator of the Nutrition Revamp player guide (Plan 14, spec § 3.1).

`python tools/mod_guide_data.py --write` builds `docs/mod-guide/data.json` from the series definitions in
`tools/mod_guide_series.py`; `--check` rebuilds it in memory and fails on any byte of difference, as
`tools/food_nutrients.py --check` does. The page reads every number from that file, so the file is never
edited by hand.

The file is `{"series": [...], "charts": {...}, "validation": [...]}`:

- `series`, ordered by id, each in the schema below (`validate_series`);
- `charts`, the source map's charts table (`mod_guide_series.CHARTS`);
- `validation`, the vanilla model's validation block (`mod_guide_series.VALIDATION`, Task 7).

A series is::

    {"id": str, "chart": str, "label": str, "units": {"x": str, "y": str},
     "badge": "live" | "kernel" | "vanilla-live" | "vanilla-model" | "study",
     "points": [[x, y], ...],              # x a number or a category string, y a finite number
     "provenance": one of
        {"kind": "artifact", "run": str, "file": str, "path": str}
        {"kind": "kernel", "commit": str, "script": str, "inputs": dict, "proof_run": str}
        {"kind": "vanilla-model", "formulas": [str], "claims": [str]}
        {"kind": "study", "science": str}
        {"kind": "dataset", "file": str, "key": str[, "build": str]}   # ruling G12
     [, "note": str]}

Badge and provenance pair: `artifact` takes `live` or `vanilla-live`; `kernel` takes `kernel`; `vanilla-model`
takes `vanilla-model`; `study` takes `study`; `dataset` takes `vanilla-model` for a file under the game's install
(read-only, its build recorded as `INSTALL_BUILD`) and `kernel` for the mod's own data under `data/` or `mod/`.

A dataset file under the install is stored as `<install>/<path inside the install>`, never as a local absolute
path, and read by joining it with `INSTALL`.

A kernel series' `commit` is the mod tree's last commit, `git log -1 --format=%H -- mod` cut to 10 characters
(a fixed length, whatever git's abbreviation setting): `build` fills it when a
definition leaves it out and refuses one that differs, so a commit under `mod/` moves `data.json` and the
`--check` gate makes it be regenerated.

The do-not-cite guard (`check_citable`, used by `read_artifact` and by the provenance validator) refuses a path
that equals a key listed for its run in `docs/reference/do-not-cite.csv`, lies inside one (a child), or contains
one (a parent: a whole object is never cited when one of its leaves is restricted). A listed key's grammar is the
register's: dotted segments, `[]`, `[*]`, `[n]` and `[a..b]` indices, `*` and `<name>` wildcards, `{a,b}`
alternatives, and several keys in one cell separated by commas. A `*` row is a whole-run prose restriction
(`n = 1`, "everything measured here, as a population"), not a key path, and is not matched, as in
`claims_check`'s rule; and each run guide's wildcard sentences (CLAUDE.md § 4 item 11, the wall-clock leaves)
are a review check, not this guard's job.
"""
import argparse, csv, json, math, os, re, subprocess, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_REL = "docs/mod-guide/data.json"
DNC_REL = "docs/reference/do-not-cite.csv"
ALIASES_REL = "docs/reference/run-aliases.csv"
CLAIMS_REL = "docs/reference/claims.tsv"
SCIENCE_REL = "docs/reference/science.tsv"
INSTALL = r"D:\SteamLibrary\steamapps\common\ProjectZomboid"
INSTALL_BUILD = "42.21"          # CLAUDE.md § 2: the install's build since 2026-10-08
INSTALL_PREFIX = "<install>/"   # how data.json names a file under the install (never a local absolute path)
MOD_DATA_DIRS = ("data/", "mod/")
COMMIT_LEN = 10

BADGES = ("live", "kernel", "vanilla-live", "vanilla-model", "study")
PROVENANCE = {
    "artifact": {"run": str, "file": str, "path": str},
    "kernel": {"commit": str, "script": str, "inputs": dict, "proof_run": str},
    "vanilla-model": {"formulas": list, "claims": list},
    "study": {"science": str},
    "dataset": {"file": str, "key": str},
}
OPTIONAL_PROVENANCE = {"dataset": {"build": str}}
BADGES_BY_KIND = {
    "artifact": ("live", "vanilla-live"),
    "kernel": ("kernel",),
    "vanilla-model": ("vanilla-model",),
    "study": ("study",),
    "dataset": ("vanilla-model", "kernel"),
}
SERIES_KEYS = {"id": str, "chart": str, "label": str, "units": dict, "badge": str, "points": list,
               "provenance": dict}
OPTIONAL_SERIES_KEYS = {"note": str}


class ProvenanceError(ValueError):
    """A series or a provenance that breaks the schema, or a source that does not resolve."""


class DoNotCite(ProvenanceError):
    """A path that is a do-not-cite key for its run, a child of one or a parent of one."""


# --- paths --------------------------------------------------------------------------------------------

_SEL_RX = re.compile(r"^\s*([^=\s]+)\s*=\s*(.*?)\s*$")


def _parse_bracket(path, i):
    """The bracket at path[i] == '[' -> (token, next index). Tokens: ('idx', int), ('all',), ('key', str),
    ('sel', field, value)."""
    j = path.find("]", i)
    if j < 0:
        raise ProvenanceError("unclosed bracket in path %r" % path)
    body = path[i + 1:j]
    if len(body) >= 2 and body[0] == body[-1] and body[0] in "\"'":
        return ("key", body[1:-1]), j + 1
    if body in ("*", ""):
        return ("all",), j + 1
    if re.fullmatch(r"-?\d+", body):
        return ("idx", int(body)), j + 1
    m = _SEL_RX.match(body)
    if m:
        return ("sel", m.group(1), m.group(2).strip("\"'")), j + 1
    raise ProvenanceError("bad bracket [%s] in path %r" % (body, path))


def _walk(node, path, i, trail, out):
    """Resolve path[i:] under node. `trail` is the concrete step list so far; each leaf appends
    (trail, value) to out. A dict step matches the longest literal key first (a ring row's keys are flat
    dotted strings such as "stomach.liquid"), before splitting on dots."""
    if i >= len(path):
        out.append((trail, node))
        return
    if path[i] == ".":
        i += 1
        if i >= len(path):
            raise ProvenanceError("a path ends with a dot: %r" % path)
    if path[i] == "[":
        tok, j = _parse_bracket(path, i)
        if tok[0] == "key":
            if not isinstance(node, dict) or tok[1] not in node:
                raise ProvenanceError("no key %r at %s" % (tok[1], _fmt(trail)))
            _walk(node[tok[1]], path, j, trail + [tok[1]], out)
        elif tok[0] == "idx":
            if not isinstance(node, list) or not -len(node) <= tok[1] < len(node):
                raise ProvenanceError("no index %d at %s" % (tok[1], _fmt(trail)))
            k = tok[1] % len(node)
            _walk(node[k], path, j, trail + [k], out)
        elif tok[0] == "all":
            if not isinstance(node, list):
                raise ProvenanceError("[*] on a non-list at %s" % _fmt(trail))
            for k, item in enumerate(node):
                _walk(item, path, j, trail + [("all", k)], out)
        else:
            if not isinstance(node, list):
                raise ProvenanceError("a selector on a non-list at %s" % _fmt(trail))
            hits = [k for k, it in enumerate(node) if isinstance(it, dict) and tok[1] in it and str(it[tok[1]]) == tok[2]]
            if len(hits) != 1:
                raise ProvenanceError("[%s=%s] matches %d elements at %s" % (tok[1], tok[2], len(hits), _fmt(trail)))
            _walk(node[hits[0]], path, j, trail + [hits[0]], out)
        return
    if not isinstance(node, dict):
        raise ProvenanceError("a key step on a non-object at %s (path %r)" % (_fmt(trail), path))
    rest = path[i:]
    cands = [k for k in node if isinstance(k, str) and k and (rest == k or rest.startswith(k + ".") or rest.startswith(k + "["))]
    if not cands:
        raise ProvenanceError("no key at %s matches %r" % (_fmt(trail), rest))
    key = max(cands, key=len)
    _walk(node[key], path, i + len(key), trail + [key], out)


def _fmt(trail):
    s = ""
    for t in trail:
        if isinstance(t, tuple):
            s += "[*]"
        elif isinstance(t, int):
            s += "[%d]" % t
        else:
            s += ("." if s else "") + t
    return s or "<root>"


def resolve(doc, path):
    """[(concrete steps, value)] for `path` under `doc`; one entry unless the path holds `[*]`."""
    out = []
    _walk(doc, path, 0, [], out)
    return out


# --- the do-not-cite guard ----------------------------------------------------------------------------

def _split_top(s, sep):
    """Split s on sep outside (), [], {} and <>."""
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch in "[{(<":
            depth += 1
        elif ch in "]})>":
            depth = max(0, depth - 1)
        if ch == sep and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


def _glob_rx(seg):
    """A key-segment glob -> a compiled regex: * any run, <name> any run, {a,b} alternatives."""
    out, i = "", 0
    while i < len(seg):
        ch = seg[i]
        if ch == "*":
            out += ".*"
        elif ch == "<" and ">" in seg[i:]:
            i = seg.index(">", i)
            out += ".*"
        elif ch == "{" and "}" in seg[i:]:
            j = seg.index("}", i)
            out += "(?:%s)" % "|".join(re.escape(a) for a in seg[i + 1:j].split(","))
            i = j
        else:
            out += re.escape(ch)
        i += 1
    return re.compile(out + r"\Z", re.S)


def _pattern_tokens(key):
    """A listed key -> [token]; a token is ('k', regex) for a key segment or ('i', lo, hi) for an index
    (('i', None, None) any index or key, ('i', rx) a non-numeric bracket matched as a key)."""
    toks = []
    for seg in _split_top(key, "."):
        m = re.match(r"^([^\[]*)((?:\[[^\]]*\])*)$", seg)
        name, brackets = (m.group(1), m.group(2)) if m else (seg, "")
        if name:
            toks.append(("k", _glob_rx(name)))
        for b in re.findall(r"\[([^\]]*)\]", brackets):
            b = b.strip()
            if b in ("", "*"):
                toks.append(("i", None, None))
            elif re.fullmatch(r"\d+", b):
                toks.append(("i", int(b), int(b)))
            elif re.fullmatch(r"\d+\.\.\d+", b):
                lo, hi = b.split("..")
                toks.append(("i", int(lo), int(hi)))
            else:
                toks.append(("ik", _glob_rx(b)))
    return toks


def _concrete_tokens(trail):
    """Concrete steps -> tokens: a key splits on dots (a listed key cannot tell a flat dotted key from a
    nested one), an index is ('n', k), and a [*] step is ('n*', n_or_None)."""
    toks = []
    for t in trail:
        if isinstance(t, tuple):
            toks.append(("n*", None))
        elif isinstance(t, int):
            toks.append(("n", t))
        else:
            toks.extend(("s", p) for p in t.split("."))
    return toks


def _tok_match(p, c):
    if p[0] == "k":
        if c[0] == "s":
            return bool(p[1].match(c[1]))
        if c[0] == "n":
            return bool(p[1].match(str(c[1])))
        return True                      # any index of a [*] read may match
    if p[0] == "ik":
        return True if c[0] == "n*" else bool(p[1].match(str(c[1])))
    lo, hi = p[1], p[2]
    if lo is None or c[0] == "n*":
        return True
    if c[0] == "n":
        return lo <= c[1] <= hi
    return c[1].isdigit() and lo <= int(c[1]) <= hi


def _overlaps(ptoks, ctoks):
    """True when one token list is a prefix of the other under matching: equal, child or parent."""
    n = min(len(ptoks), len(ctoks))
    return all(_tok_match(ptoks[k], ctoks[k]) for k in range(n))     # an empty read (the root) contains every key


_DNC_CACHE = {}


def load_dnc(root=REPO):
    """{run: [(listed key, tokens)]} from do-not-cite.csv; a `*` row and an empty key are left out."""
    path = os.path.join(root, DNC_REL)
    if path not in _DNC_CACHE:
        dnc = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    cell = (row.get("key") or "").strip()
                    if not cell:
                        continue
                    for key in _split_top(cell, ","):
                        key = key.strip()
                        if key and key != "*":
                            dnc.setdefault(row.get("run", ""), []).append((key, _pattern_tokens(key)))
        _DNC_CACHE[path] = dnc
    return _DNC_CACHE[path]


def load_aliases(root=REPO):
    path = os.path.join(root, ALIASES_REL)
    out = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                if row.get("alias"):
                    out[row["alias"]] = row
    return out


def real_run(run, root=REPO):
    a = load_aliases(root)
    return a[run]["run"] if run in a else run


def check_citable(run, trail, root=REPO, leaf=False):
    """Raise DoNotCite when the concrete steps `trail` (or the path string) under `run` touch a listed key.

    `leaf` says the value read is a scalar: a scalar holds no children, so a longer listed key (one that a
    `*` or `<name>` segment lets match its prefix) cannot lie inside it and does not refuse it. Without a
    document (a path string alone) the check stays conservative and refuses such a prefix."""
    if isinstance(trail, str):
        trail = _path_steps(trail)
    ctoks = _concrete_tokens(trail)
    dnc = load_dnc(root)
    real = real_run(run, root)
    for r in (run, real) if real != run else (run,):
        for key, ptoks in dnc.get(r, ()):
            if leaf and len(ctoks) < len(ptoks):
                continue
            if _overlaps(ptoks, ctoks):
                rel = "equals" if len(ptoks) == len(ctoks) else ("is inside" if len(ctoks) > len(ptoks) else "contains")
                raise DoNotCite("%s %s %s the do-not-cite key %s" % (r, _fmt(trail), rel, key))


def _path_steps(path):
    """A path string -> steps without a document (dots split, brackets parsed); for checking a path alone."""
    steps, i = [], 0
    while i < len(path):
        if path[i] == ".":
            i += 1
            continue
        if path[i] == "[":
            tok, i = _parse_bracket(path, i)
            steps.append(tok[1] if tok[0] in ("key", "idx") else (tok[0], 0))   # a selector checks as any index
            continue
        j = i
        while j < len(path) and path[j] not in ".[":
            j += 1
        steps.append(path[i:j])
        i = j
    return steps


# --- readers ------------------------------------------------------------------------------------------

_JSON_CACHE = {}


def _load_json(path):
    if path not in _JSON_CACHE:
        with open(path, encoding="utf-8") as fh:
            _JSON_CACHE[path] = json.load(fh)
    return _JSON_CACHE[path]


def artifact_file(run, file, root=REPO):
    real = real_run(run, root)
    path = os.path.join(root, "testing", "artifacts", real, *file.replace("\\", "/").split("/"))
    if not os.path.isfile(path):
        raise ProvenanceError("artifact %s has no file %s" % (real, file))
    return path


_ALT_RX = re.compile(r"\{([^{}]*)\}")


def expand(path):
    """A path's `{a,b,...}` alternatives expanded in order (several groups expand as a product, left to right):
    `x.{1,2}.y` -> [`x.1.y`, `x.2.y`]; a path without braces is itself. Lets one provenance name the same leaf
    under several keys (a dict has no `[*]`), as a do-not-cite key's `{a,b}` does."""
    m = _ALT_RX.search(path)
    if not m:
        return [path]
    out = []
    for alt in m.group(1).split(","):
        out.extend(expand(path[:m.start()] + alt.strip() + path[m.end():]))
    return out


def read_artifact(run, file, path, root=REPO):
    """The value at `path` in testing/artifacts/<run>/<file>; a list of values when the path holds `[*]` or
    `{a,b}` alternatives (one value per alternative, in the order written).

    Paths are dotted keys with `[n]`, `[*]`, `["literal.key"]` and `[field=value]` steps; a dict step
    matches the longest literal key first. Refuses (DoNotCite) a do-not-cite key, a child of one and a
    parent of one, checking every concrete path the read touches."""
    alts = expand(path)
    if len(alts) > 1:
        return [read_artifact(run, file, p, root) for p in alts]
    doc = _load_json(artifact_file(run, file, root))
    hits = resolve(doc, path)
    seen = set()
    for trail, value in hits:
        leaf = not isinstance(value, (dict, list))
        key = (tuple(("*",) if isinstance(t, tuple) else (t,) for t in trail), leaf)
        if key not in seen:
            seen.add(key)
            check_citable(run, trail, root, leaf)
    return [v for _, v in hits] if _is_wild(path) else hits[0][1]


def _is_wild(path):
    return any(isinstance(t, tuple) and t[0] == "all" for t in _path_steps(path))


def dataset_side(file, root=REPO, install=INSTALL):
    """'vanilla' for `<install>/...` (a file under the install), 'mod' for one under the repo's data/ or mod/;
    else raise. A local absolute path is refused: data.json never carries one."""
    rel = file.replace("\\", "/")
    if os.path.isabs(file) or re.match(r"^[A-Za-z]:", file) or rel.startswith("/"):
        raise ProvenanceError("dataset file %s is a local absolute path; name a file under the install as %s..."
                              % (file, INSTALL_PREFIX))
    if rel == ".." or rel.startswith("../") or "/../" in rel or rel.endswith("/.."):
        raise ProvenanceError("dataset file %s leaves its tree" % file)
    if rel.startswith(INSTALL_PREFIX):
        if not rel[len(INSTALL_PREFIX):]:
            raise ProvenanceError("dataset file %s names no file under the install" % file)
        return "vanilla"
    if not rel.startswith(MOD_DATA_DIRS):
        raise ProvenanceError("a repository dataset file sits under data/ or mod/: %s" % file)
    return "mod"


def dataset_path(file, root=REPO, install=INSTALL):
    """The local path of a dataset file: `<install>/x` joined with `install`, a repo path with `root`."""
    rel = file.replace("\\", "/")
    if dataset_side(file, root, install) == "vanilla":
        return os.path.join(install, *rel[len(INSTALL_PREFIX):].split("/"))
    return os.path.join(root, *rel.split("/"))


def _block_end(text, start):
    """The index just past the `}` closing the block whose body starts at `start` (after its `{`)."""
    depth, j = 1, start
    while j < len(text) and depth:
        depth += {"{": 1, "}": -1}.get(text[j], 0)
        j += 1
    return j


def _script_value(text, key):
    """`Module.Item.Field` out of a PZ script text: the item block inside that module's block, and the field
    among the item's own lines (a nested sub-block such as `component FluidContainer { ... }` is skipped)."""
    parts = key.split(".")
    if len(parts) != 3:
        raise ProvenanceError("a script key is Module.Item.Field: %r" % key)
    module, item, field = parts
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    mods = [mm for mm in re.finditer(r"\bmodule\s+%s\s*\{" % re.escape(module), text)]
    if not mods:
        raise ProvenanceError("no module %s in the script" % module)
    m, body = None, ""
    for mm in mods:
        body = text[mm.end():_block_end(text, mm.end()) - 1]
        m = re.search(r"\bitem\s+%s\s*\{" % re.escape(item), body)
        if m:
            break
    if not m:
        raise ProvenanceError("no item %s in module %s" % (item, module))
    block = body[m.end():_block_end(body, m.end()) - 1]
    flat, depth = "", 0
    for ch in block:                                       # the item's own lines: nested blocks dropped
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        elif depth == 0:
            flat += ch
    block = flat
    f = re.search(r"^\s*%s\s*=\s*([^,\n]*)" % re.escape(field), block, flags=re.M | re.I)
    if not f:
        raise ProvenanceError("item %s has no field %s" % (item, field))
    raw = f.group(1).strip()
    try:
        return float(raw) if re.search(r"[.eE]", raw) else int(raw)
    except ValueError:
        return raw


def read_dataset(file, key, root=REPO, install=INSTALL):
    """The value at `key` in a dataset file: a JSON path (read_artifact's grammar) in a .json file, or
    `Module.Item.Field` in a game script (.txt); a list of values for `{a,b}` alternatives (expand)."""
    alts = expand(key)
    if len(alts) > 1:
        return [read_dataset(file, k, root, install) for k in alts]
    full = dataset_path(file, root, install)
    if not os.path.isfile(full):
        raise ProvenanceError("dataset file %s does not exist" % file)
    if full.lower().endswith(".json"):
        hits = resolve(_load_json(full), key)
        return [v for _, v in hits] if _is_wild(key) else hits[0][1]
    with open(full, encoding="utf-8", errors="replace") as fh:
        return _script_value(fh.read(), key)


# --- the kernel commit, the registers -----------------------------------------------------------------

def kernel_commit(root=REPO):
    """`git log -1 --format=%H -- mod` cut to 10 characters: the mod tree's last commit."""
    p = subprocess.run(["git", "-C", root, "log", "-1", "--format=%H", "--", "mod"], capture_output=True, text=True)
    sha = p.stdout.strip()[:COMMIT_LEN]
    if p.returncode != 0 or not sha:
        raise ProvenanceError("no commit touches mod/ in %s" % root)
    return sha


_IDS_CACHE = {}


def _register_ids(root, rel):
    path = os.path.join(root, rel)
    if path not in _IDS_CACHE:
        ids = set()
        if os.path.exists(path):
            with open(path, encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh, delimiter="\t"):
                    ids.add((row.get("id") or "").strip())
        _IDS_CACHE[path] = ids
    return _IDS_CACHE[path]


def _formula_ids():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import vanilla_model                                          # lazy: only a vanilla-model series needs it
    return set(vanilla_model.FORMULAS)


# --- validation ---------------------------------------------------------------------------------------

def _typed(d, spec, optional, where):
    for k, t in spec.items():
        if k not in d:
            raise ProvenanceError("%s: missing %s" % (where, k))
        if not isinstance(d[k], t) or (t is str and not d[k]):
            raise ProvenanceError("%s: %s must be a non-empty %s" % (where, k, t.__name__))
    for k in d:
        if k not in spec and k not in optional:
            raise ProvenanceError("%s: unknown key %s" % (where, k))
    for k, t in optional.items():
        if k in d and (not isinstance(d[k], t) or (t is str and not d[k])):
            raise ProvenanceError("%s: %s must be a non-empty %s" % (where, k, t.__name__))


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def validate_series(s, root=REPO, install=INSTALL, commit=None, charts=None):
    """Check one series against the schema, its badge against its provenance kind, and its provenance
    against its source (the do-not-cite guard included). Fills a kernel series' missing `commit`."""
    if not isinstance(s, dict):
        raise ProvenanceError("a series is a dict: %r" % (s,))
    where = "series %s" % s.get("id", "?")
    _typed(s, SERIES_KEYS, OPTIONAL_SERIES_KEYS, where)
    if s["badge"] not in BADGES:
        raise ProvenanceError("%s: badge %r is not one of %s" % (where, s["badge"], ", ".join(BADGES)))
    _typed(s["units"], {"x": str, "y": str}, {}, where + " units")
    if not s["points"]:
        raise ProvenanceError("%s: no points" % where)
    for pt in s["points"]:
        if not isinstance(pt, list) or len(pt) != 2:
            raise ProvenanceError("%s: a point is [x, y]: %r" % (where, pt))
        if not (_number(pt[0]) or (isinstance(pt[0], str) and pt[0])) or not _number(pt[1]):
            raise ProvenanceError("%s: a point's x is a finite number or a category and its y a finite number: %r" % (where, pt))
    if charts is not None:
        if s["chart"] not in charts:
            raise ProvenanceError("%s: chart %s is not in the charts table" % (where, s["chart"]))
        if s["id"] not in charts[s["chart"]]["series"]:
            raise ProvenanceError("%s: chart %s does not list it" % (where, s["chart"]))
    p = s["provenance"]
    kind = p.get("kind")
    if kind not in PROVENANCE:
        raise ProvenanceError("%s: provenance kind %r is not one of %s" % (where, kind, ", ".join(PROVENANCE)))
    body = {k: v for k, v in p.items() if k != "kind"}
    if kind == "kernel" and "commit" not in body and commit is not None:
        p["commit"] = body["commit"] = commit
    _typed(body, PROVENANCE[kind], OPTIONAL_PROVENANCE.get(kind, {}), where + " provenance")
    if s["badge"] not in BADGES_BY_KIND[kind]:
        raise ProvenanceError("%s: badge %s does not go with a %s provenance" % (where, s["badge"], kind))
    if kind == "artifact":
        read_artifact(p["run"], p["file"], p["path"], root)
    elif kind == "kernel":
        if commit is not None and p["commit"] != commit:
            raise ProvenanceError("%s: kernel commit %s is not mod/'s last commit %s" % (where, p["commit"], commit))
        if not os.path.isfile(os.path.join(root, *p["script"].split("/"))):
            raise ProvenanceError("%s: script %s does not exist" % (where, p["script"]))
        if not os.path.isdir(os.path.join(root, "testing", "artifacts", real_run(p["proof_run"], root))):
            raise ProvenanceError("%s: proof run %s has no artifact folder" % (where, p["proof_run"]))
        try:
            json.dumps(p["inputs"], sort_keys=True, allow_nan=False)
        except (TypeError, ValueError) as e:
            raise ProvenanceError("%s: inputs are not plain JSON (%s)" % (where, e))
    elif kind == "vanilla-model":
        if not p["formulas"] or not p["claims"]:
            raise ProvenanceError("%s: a vanilla-model provenance names its formulas and claims" % where)
        known = _formula_ids()
        bad = [f for f in p["formulas"] if f not in known]
        if bad:
            raise ProvenanceError("%s: unknown formulas %s" % (where, ", ".join(map(str, bad))))
        ids = _register_ids(root, CLAIMS_REL)
        bad = [c for c in p["claims"] if c not in ids]
        if bad:
            raise ProvenanceError("%s: claims not in the register %s" % (where, ", ".join(map(str, bad))))
    elif kind == "study":
        if p["science"] not in _register_ids(root, SCIENCE_REL):
            raise ProvenanceError("%s: %s is not a science register row" % (where, p["science"]))
    elif kind == "dataset":
        side = dataset_side(p["file"], root, install)
        want = "vanilla-model" if side == "vanilla" else "kernel"
        if s["badge"] != want:
            raise ProvenanceError("%s: a %s dataset file takes the badge %s" % (where, side, want))
        if side == "vanilla" and p.get("build") != INSTALL_BUILD:
            raise ProvenanceError("%s: a file under the install records its build %s" % (where, INSTALL_BUILD))
        if side == "mod" and "build" in p:
            raise ProvenanceError("%s: a repository file records no install build" % where)
        read_dataset(p["file"], p["key"], root, install)
    return s


# --- build and write ----------------------------------------------------------------------------------

def _series_module():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import mod_guide_series                                        # lazy: Task 4's definitions
    return mod_guide_series


def coverage_gaps(series_ids, charts, pending):
    """Ruling T3, the reverse-coverage gate: the chart-listed ids with no series that `pending` does not name, and
    the pending ids that are built after all or that no chart lists (each a stale entry). Returns (missing, stale)."""
    built = set(series_ids)
    listed = {i for c in charts.values() for i in c["series"]}
    pend = set(pending)
    missing = sorted(listed - built - pend)
    stale = sorted((pend & built) | (pend - listed))
    return missing, stale


def build(series_defs=None, root=REPO, charts=None, validation=None, install=INSTALL, pending=None):
    """The data file's dict: every definition run, each series validated, series ordered by id. `pending` (the
    series module's PENDING_LIVE when None) names the chart-listed ids that wait on a live run: every other id a
    chart lists must be built (coverage_gaps), and a pending id must be neither built nor unlisted."""
    if series_defs is None or charts is None or validation is None:
        mod = _series_module()
        if pending is None:           # the module's pending list goes with the module's charts only
            pending = getattr(mod, "PENDING_LIVE", ()) if charts is None else ()
        series_defs = mod.SERIES_DEFS if series_defs is None else series_defs
        charts = mod.CHARTS if charts is None else charts
        validation = mod.VALIDATION if validation is None else validation
    pending = () if pending is None else pending
    commit = None
    series = []
    for fn in series_defs:
        got = fn()
        for s in (got if isinstance(got, list) else [got]):
            if isinstance(s, dict) and isinstance(s.get("provenance"), dict) and s["provenance"].get("kind") == "kernel" and commit is None:
                commit = kernel_commit(root)
            series.append(validate_series(s, root, install, commit, charts))
    ids = [s["id"] for s in series]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    if dups:
        raise ProvenanceError("duplicate series ids: %s" % ", ".join(dups))
    missing, stale = coverage_gaps(ids, charts, pending)
    if missing:
        raise ProvenanceError("charts list series with no definition and not pending: %s" % ", ".join(missing))
    if stale:
        raise ProvenanceError("pending ids that are built or that no chart lists: %s" % ", ".join(stale))
    if not isinstance(validation, list):
        raise ProvenanceError("validation is a list")
    return {"series": sorted(series, key=lambda s: s["id"]), "charts": charts, "validation": validation}


def dumps(data):
    """sort_keys, indent=1, repr-exact floats (no rounding), UTF-8 kept, a trailing newline."""
    return json.dumps(data, sort_keys=True, indent=1, ensure_ascii=False, allow_nan=False) + "\n"


def main(argv=None, root=REPO, series_defs=None, charts=None, validation=None, pending=None, out=None):
    """`out` overrides the data file's path (a test's scratch copy); the default is <root>/docs/mod-guide/data.json."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="fail when docs/mod-guide/data.json is out of date")
    g.add_argument("--write", action="store_true", help="regenerate docs/mod-guide/data.json")
    args = ap.parse_args(argv)
    try:
        text = dumps(build(series_defs, root, charts, validation, pending=pending))
    except ProvenanceError as e:
        print("mod_guide_data: %s" % e, file=sys.stderr)
        return 2
    out = out or os.path.join(root, *OUT_REL.split("/"))
    if args.write:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print("wrote %s (%d bytes)" % (OUT_REL, len(text.encode("utf-8"))))
        return 0
    try:
        with open(out, encoding="utf-8", newline="") as fh:
            old = fh.read().replace("\r\n", "\n")      # a checkout under core.autocrlf=true may hold CRLF
    except OSError:
        print("%s is missing: run --write" % OUT_REL, file=sys.stderr)
        return 1
    if old == text:
        print("%s in sync" % OUT_REL)
        return 0
    a, b = old.split("\n"), text.split("\n")
    k = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
    print("%s is out of date: first difference at line %d (run --write)" % (OUT_REL, k + 1), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
