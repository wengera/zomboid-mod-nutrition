#!/usr/bin/env python3
"""The PZA/1 generator: one schema, three targets (Plan 22 spec section 4).

    python tools/pza_schema.py --write     regenerate the three targets
    python tools/pza_schema.py --check     exit 1 when any target differs from a fresh render

The schema `testing/agent/base/schema/pza1.json` is the one source of the PZAgent protocol. From it this tool renders
the Lua header `testing/PZAgent/PZAgent/42/media/lua/shared/PZAgent_Schema.lua` (the field orders and enums as
`PZA.schema`, and the positional encoders `PZA.enc.*`), the Python module `testing/agent/base/pza1.py` (the same
orders and enums, `encode`, `decode`, `merge_delta` and the command dataclasses) and the LLM tool descriptions
`testing/agent/base/schema/tools.json` (one Anthropic tool per action type). A generated file is never edited by hand.

`load()` refuses a schema whose parts disagree (an x-order that is not its properties, an enum without its per-kind
definitions, a property without a description), so no field, kind or enum reaches a target unchecked. A group's fields
are only ever appended at the end of its x-order (PZA/1.1: PZAgent 1.1's `me` and `cost`); its `x-prior` names the
oldest arity a writer used (before the first append), and `decode` reads a group array of any arity from it up to the
full order with the trailing fields None, so a log written before an append still replays; a shorter or a longer
array is refused. `--check`
compares with CRLF read as LF on both sides; `--write` writes LF, UTF-8. Stdlib only.
"""
import argparse
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_REL = "testing/agent/base/schema/pza1.json"
SCHEMA = os.path.join(REPO, *SCHEMA_REL.split("/"))
LUA_REL = "testing/PZAgent/PZAgent/42/media/lua/shared/PZAgent_Schema.lua"
PY_REL = "testing/agent/base/pza1.py"
TOOLS_REL = "testing/agent/base/schema/tools.json"
ENVELOPE = ("kind", "seq", "tick", "wallMs")
ARG_TYPES = {"integer": "int", "number": "float", "string": "str"}
ARG_ENUMS = ("gait", "ikind", "filter")
LUA_KEYWORDS = frozenset("and break do else elseif end false for function if in local nil not or repeat return then "
                         "true until while".split())


# ---- the schema model -----------------------------------------------------------------------------------------

def _ref(prop):
    """The $defs name a property points at (directly or inside its anyOf), or None."""
    if "$ref" in prop:
        return prop["$ref"].rsplit("/", 1)[-1]
    for alt in prop.get("anyOf", ()):
        if "$ref" in alt:
            return alt["$ref"].rsplit("/", 1)[-1]
    return None


def _need(cond, msg):
    if not cond:
        raise ValueError("pza1.json: " + msg)


def _check_descriptions(node, path):
    if isinstance(node, dict):
        for name, prop in (node.get("properties") or {}).items():
            d = prop.get("description")
            _need(isinstance(d, str) and d.strip() and "\n" not in d, "%s.%s has no one-line description" % (path, name))
        for k, v in node.items():
            _check_descriptions(v, path + "/" + k)
    elif isinstance(node, list):
        for v in node:
            _check_descriptions(v, path)


def load(path=SCHEMA):
    """The schema as the generator's model; a ValueError names the first inconsistency."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    defs = raw["$defs"]
    _check_descriptions(raw, "")
    for name, d in defs.items():
        _need(d.get("description"), "$defs.%s has no description" % name)

    kinds = list(raw["x-kinds"])
    _need(kinds == [n for n, d in defs.items() if d.get("x-role") == "kind"], "x-kinds is not the kind definitions")
    _need([_ref(r) for r in raw["oneOf"]] == kinds, "the top-level oneOf is not x-kinds")
    for k in kinds:
        _need(defs[k].get("x-encoding") in ("positional", "keyed"), "%s has no x-encoding" % k)
        _need(defs[k]["properties"]["kind"].get("const") == k, "%s.kind is not const %s" % (k, k))
    positional = [k for k in kinds if defs[k]["x-encoding"] == "positional"]

    def order_of(name):
        d = defs[name]
        props = list(d["properties"])
        if d.get("x-encoding") == "positional":
            o = list(d["x-order"])
            _need(len(set(o)) == len(o) and set(o) == set(props), "%s: x-order is not its properties" % name)
            _need(set(d.get("required", ())) == set(o), "%s: required is not its x-order" % name)
            return o
        return props

    order = {k: order_of(k) for k in kinds}
    for k in kinds:
        _need(tuple(order[k][:4]) == ENVELOPE, "%s: the envelope is not first" % k)
        _need(set(ENVELOPE) <= set(defs[k].get("required", ())), "%s: the envelope is not required" % k)

    groups, records, shapes = {}, {}, {}

    def shape(owner, field, prop, top):
        ref = _ref(prop)
        if ref is not None and defs[ref].get("x-role") == "group":
            _need(top, "%s.%s: a group sits only at a kind's top level" % (owner, field))
            gname = defs[ref].get("x-group", ref)
            visit_group(gname, ref)
            return ("group", gname)
        if ref is not None and defs[ref].get("x-role") == "record":
            visit_record(ref)
            return ("rec", ref)
        if prop.get("type") == "array":
            iref = _ref(prop.get("items", {}))
            if iref is not None and defs[iref].get("x-role") == "record":
                visit_record(iref)
                return ("list", iref)
            _need(iref is None or "enum" in defs[iref], "%s.%s: an array of %s" % (owner, field, iref))
            return ("vlist", None)
        _need(ref is None or "enum" in defs[ref], "%s.%s: a reference to %s" % (owner, field, ref))
        return None

    def fill(owner, defname, top):
        d = defs[defname]
        _need(d.get("x-encoding") == "positional", "%s is not positional" % defname)
        sh = {}
        for f in order_of(defname):
            s = shape(owner, f, d["properties"][f], top)
            if s is not None:
                sh[f] = s
        shapes[owner] = sh

    def visit_group(gname, defname):
        if gname in groups:
            _need(groups[gname]["def"] == defname, "group %s names two definitions" % gname)
            return
        order_g = order_of(defname)
        prior = defs[defname].get("x-prior")
        _need(prior is None or (type(prior) is int and 0 < prior < len(order_g)),
              "%s: x-prior is not an arity below its x-order's" % defname)
        groups[gname] = {"def": defname, "order": order_g, "prior": prior}
        fill(gname, defname, False)

    def visit_record(rname):
        if rname in records:
            return
        records[rname] = None                       # a placeholder against a cycle; filled after its children
        _need(rname not in groups, "%s is a group and a record" % rname)
        fill(rname, rname, False)
        del records[rname]
        records[rname] = {"def": rname, "order": order_of(rname)}   # children first: the Lua definition order

    for k in positional:
        fill(k, k, True)
    for name, d in defs.items():
        if d.get("x-role") in ("group", "record"):
            _need(name in records or d.get("x-group", name) in groups, "%s is never reached from a kind" % name)
    _need(not (set(groups) & set(records)), "a name is both a group and a record")

    def enum(name):
        return list(defs[name]["enum"])

    action_types = enum("actionType")

    def per_type(prefix, role):
        found = {d.get("x-type"): n for n, d in defs.items() if d.get("x-role") == role}
        _need(set(found) == set(action_types), "the %s definitions are not the action types" % role)
        for t, n in found.items():
            _need(n == prefix + t, "%s names type %s" % (n, t))
        return found

    per_type("args_", "args")
    per_type("result_", "result")
    actions = {}
    for t in action_types:
        d = defs["args_" + t]
        req = list(d.get("required", ()))
        args = []
        for name, prop in d["properties"].items():
            ref = _ref(prop)
            if ref is not None:
                _need(ref in ARG_ENUMS, "args_%s.%s: a reference to %s" % (t, name, ref))
                kind = ref
            else:
                _need(prop.get("type") in ARG_TYPES, "args_%s.%s: type %s" % (t, name, prop.get("type")))
                kind = ARG_TYPES[prop["type"]]
            has_default = "default" in prop
            _need(has_default != (name in req), "args_%s.%s: required exactly when it has no default" % (t, name))
            if has_default and ref is not None:
                _need(prop["default"] in enum(ref), "args_%s.%s: the default is not in %s" % (t, name, ref))
            args.append({"name": name, "kind": kind, "default": prop.get("default"), "has_default": has_default,
                         "prop": prop})
        names = [a["name"] for a in args]
        first_default = next((i for i, a in enumerate(args) if a["has_default"]), len(args))
        _need(all(a["has_default"] for a in args[first_default:]), "args_%s: a default before a required field" % t)
        _need(req == names[:first_default], "args_%s: required is not the leading fields" % t)
        actions[t] = {"args": args, "description": d["description"]}

    event_kinds = enum("eventKind")
    found = {n[len("event_"):]: n for n, d in defs.items() if d.get("x-role") == "event"}
    _need(set(found) == set(event_kinds), "the event_ definitions are not eventKind's enum")
    _need([_ref(r) for r in defs["event"]["oneOf"]] == ["event_" + k for k in event_kinds], "event.oneOf is not eventKind")
    events = {}
    for k in event_kinds:
        d = defs["event_" + k]
        _need(d["properties"]["event"].get("const") == k, "event_%s.event is not const %s" % (k, k))
        fields = [f for f in d["properties"] if f != "event"]
        _need(set(d.get("required", ())) == set(fields), "event_%s: required is not its fields" % k)
        _need(not set(fields) & set(order["event"]), "event_%s shadows an event field" % k)
        events[k] = fields
    _need(_ref(defs["hello"]["properties"]["caps"]["items"]) == "actionType", "hello.caps is not action types")
    _need(defs["hello"]["properties"]["proto"].get("const") == raw["x-proto"], "hello.proto is not x-proto")

    return {
        "raw": raw, "proto": raw["x-proto"], "kinds": kinds, "positional": positional, "order": order,
        "groups": groups, "records": records, "shapes": shapes,
        "reasons": enum("reason"), "action_types": action_types, "actions": actions, "gaits": enum("gait"),
        "ikinds": enum("ikind"), "filters": enum("filter"), "act_states": enum("actState"),
        "event_kinds": event_kinds, "events": events, "map_modes": enum("mapMode"),
    }


# ---- the Lua header -------------------------------------------------------------------------------------------

def _lq(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _lkey(s):
    if re.match(r"^[A-Za-z_]\w*$", s) and s not in LUA_KEYWORDS:
        return s
    return "[" + _lq(s) + "]"


def _lidx(var, f):
    k = _lkey(f)
    return var + ("." + k if not k.startswith("[") else k)


def _llist(xs):
    return "{ " + ", ".join(_lq(x) for x in xs) + " }" if xs else "{}"


def _lset(xs):
    return "{ " + ", ".join("%s = true" % _lkey(x) for x in xs) + " }"


def _lua_field(sch, owner, var, f, same=False):
    s = sch["shapes"].get(owner, {}).get(f)
    val = _lidx(var, f)
    if s is None:
        return "v(%s)" % val
    form, name = s
    if form == "group":
        enc = "enc_%s(%s)" % (name, val)
        return '(same.%s == true and "true" or %s)' % (name, enc) if same else enc
    if form == "rec":
        return "enc_%s(%s)" % (name, val)
    if form == "list":
        return "list(%s, enc_%s)" % (val, name)
    return "list(%s, v)" % val


def _lua_comment(sch, owner, label, order, defname):
    lines = ["-- %s: %s" % (label, sch["raw"]["$defs"][defname]["description"])]
    props = sch["raw"]["$defs"][defname]["properties"]
    for f in order:
        lines.append("--   %s: %s" % (f, props[f]["description"]))
    return lines


def _lua_encoder(sch, owner, label):
    d = sch["groups"][owner] if owner in sch["groups"] else sch["records"][owner]
    order = d["order"]
    out = _lua_comment(sch, owner, label, order, d["def"])
    out.append("local function enc_%s(t)" % owner)
    out.append('    if t == nil then return "null" end')
    parts = [_lua_field(sch, owner, "t", f) for f in order]
    out.append('    return "[" .. ' + ' .. "," .. '.join(parts) + ' .. "]"')
    out.append("end")
    out.append("PZA.enc.%s = enc_%s" % (owner, owner))
    out.append("")
    return out


def _lua_kind(sch, kind):
    out = _lua_comment(sch, kind, "the %s line" % kind, sch["order"][kind], kind)
    elides = any(s[0] == "group" for s in sch["shapes"][kind].values())
    out.append("PZA.enc.%s = function(b%s)" % (kind, ", same" if elides else ""))
    if elides:
        out.append("    same = same or NONE")
    out.append("    return " + _lq("[" + json.dumps(kind)))
    for f in sch["order"][kind][1:]:
        out.append('        .. "," .. ' + _lua_field(sch, kind, "b", f, same=elides))
    out.append('        .. "]"')
    out.append("end")
    out.append("")
    return out


LUA_HEAD = """-- GENERATED by python tools/pza_schema.py from testing/agent/base/schema/pza1.json — never edit; PZA.enc is the positional encoder (spec § 8).
-- PZA.schema holds the protocol's field orders and enums; PZA.enc.frame and PZA.enc.map write a positional line (a JSON
-- array in the schema's field order, opening with the kind) as straight-line string builders: no pairs walk, no sort.
-- Every group and record encoder is exported as PZA.enc.<name> (ruling S-1), and each answers "null" for nil. A frame's
-- same[group] == true writes true in that group's place (a delta). Loads after PZAgent_Core.lua (shared/, by name):
-- PZA.enc.v renders a number by PZA.json's rule and sends a string through PZA.json, whose escape (jsonString) is
-- local to Core and so is reused, never copied.
PZA = PZA or {}
"""

LUA_RUNTIME = """PZA.enc = {}
local floor, abs, huge, tostring, concat = math.floor, math.abs, math.huge, tostring, table.concat
local fmt = string.format
local NONE = {}

-- One value: nil is null; a boolean true or false; a number as PZA.json renders it (NaN and +-Inf null, an integral
-- value under 1e15 through the 0-decimal format, any other through tostring); anything else through PZA.json.
local function v(x)
    local t = type(x)
    if t == "number" then
        if x ~= x or x == huge or x == -huge then return "null" end
        if x == floor(x) and abs(x) < 1e15 then return fmt("%.0f", x) end
        return tostring(x)
    end
    if x == nil then return "null" end
    if t == "boolean" then return x and "true" or "false" end
    return PZA.json(x)
end
PZA.enc.v = v

-- A Lua array (never a Java list) through one element encoder; nil is null.
local function list(a, f)
    if a == nil then return "null" end
    local n = #a
    if n == 0 then return "[]" end
    local out = {}
    for i = 1, n do out[i] = f(a[i]) end
    return "[" .. concat(out, ",") .. "]"
end

"""


def render_lua(sch=None):
    sch = sch or load()
    L = [LUA_HEAD]
    L.append("PZA.schema = {")
    L.append("    PROTO = %s," % _lq(sch["proto"]))
    L.append("    order = {")
    for k in sch["kinds"]:
        L.append("        %s = %s," % (_lkey(k), _llist(sch["order"][k])))
    L.append("    },")
    L.append("    groups = {")
    for g, d in sch["groups"].items():
        L.append("        %s = %s," % (_lkey(g), _llist(d["order"])))
    L.append("    },")
    L.append("    records = {")
    for r, d in sch["records"].items():
        L.append("        %s = %s," % (_lkey(r), _llist(d["order"])))
    L.append("    },")
    L.append("    reasons = %s," % _lset(sch["reasons"]))
    L.append("    actions = {")
    for t in sch["action_types"]:
        L.append("        %s = %s," % (_lkey(t), _llist([a["name"] for a in sch["actions"][t]["args"]])))
    L.append("    },")
    L.append("    gaits = %s," % _lset(sch["gaits"]))
    L.append("    ikinds = %s," % _lset(sch["ikinds"]))
    L.append("    filters = %s," % _lset(sch["filters"]))
    L.append("    states = %s," % _lset(sch["act_states"]))
    L.append("    mapModes = %s," % _lset(sch["map_modes"]))
    L.append("    events = {")
    for k in sch["event_kinds"]:
        L.append("        %s = %s," % (_lkey(k), _llist(sch["events"][k])))
    L.append("    },")
    L.append("}")
    L.append("")
    L.append(LUA_RUNTIME.rstrip("\n"))
    L.append("")
    for r in sch["records"]:
        L.extend(_lua_encoder(sch, r, "record " + r))
    for g in sch["groups"]:
        L.extend(_lua_encoder(sch, g, "group " + g))
    for k in sch["positional"]:
        L.extend(_lua_kind(sch, k))
    return "\n".join(L).rstrip("\n") + "\n"


# ---- the Python module ----------------------------------------------------------------------------------------

def _pl(o):
    if isinstance(o, str):
        return json.dumps(o)
    if isinstance(o, (list, tuple)):
        inner = ", ".join(_pl(x) for x in o)
        return "(" + inner + ("," if len(o) == 1 else "") + ")"
    if isinstance(o, dict):
        return "{" + ", ".join("%s: %s" % (_pl(k), _pl(v)) for k, v in o.items()) + "}"
    return repr(o)


def _pdict(name, d, comment=None):
    out = ["# " + comment] if comment else []
    out.append("%s = {" % name)
    for k, v in d.items():
        out.append("    %s: %s," % (_pl(k), _pl(v)))
    out.append("}")
    return out


PY_HEAD = '''"""GENERATED by python tools/pza_schema.py from testing/agent/base/schema/pza1.json — never edit.

PZA/1 in Python: the line kinds, field orders and enums, `encode` (the fake mod's writer: the positional line for
frame and map, keyed sorted JSON for the rest), `decode` (a parsed line to its keyed dict, an elided group as SAME),
`merge_delta` and the command dataclasses. A number is written by the Lua rule (NaN and +-Inf null, an integral value
under 1e15 without decimals) except that a fractional float is written round-trip (repr), as Kahlua's Double.toString
does.
"""
import dataclasses
import json
import math
from typing import ClassVar
'''

PY_RUNTIME = '''

class _Same:
    """An elided group of a delta frame: the group equals the base frame's."""
    __slots__ = ()

    def __repr__(self):
        return "SAME"


SAME = _Same()
_POS = dict(GROUPS, **RECORDS)
_POS.update({k: ORDER[k] for k in POSITIONAL})


def _v(x):
    if x is None:
        return "null"
    if x is True:
        return "true"
    if x is False:
        return "false"
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        if x != x or x in (math.inf, -math.inf):
            return "null"
        if x == math.floor(x) and abs(x) < 1e15:
            return "%.0f" % x
        return repr(x)
    if isinstance(x, str):
        return json.dumps(x, ensure_ascii=False)
    raise TypeError("PZA/1: not a scalar: %r" % (x,))


def _keys(owner, d):
    extra = set(d) - set(_POS[owner])
    if extra:
        raise ValueError("PZA/1 %s: unknown fields %s" % (owner, sorted(extra)))


def _enc(owner, d, same=()):
    if d is None:
        return "null"
    if not isinstance(d, dict):
        raise TypeError("PZA/1 %s: not a dict: %r" % (owner, d))
    _keys(owner, d)
    shapes = SHAPES.get(owner, {})
    out = []
    for f in _POS[owner]:
        x = d.get(f)
        s = shapes.get(f)
        if f in same:
            out.append("true")
        elif s is None:
            out.append(_v(x))
        elif s[0] in ("group", "rec"):
            out.append(_enc(s[1], x))
        elif x is None:
            out.append("null")
        elif s[0] == "list":
            out.append("[" + ",".join(_enc(s[1], e) for e in x) + "]")
        else:
            out.append("[" + ",".join(_v(e) for e in x) + "]")
    return "[" + ",".join(out) + "]"


def _keyed_check(body):
    kind = body.get("kind")
    absent = [f for f in ENVELOPE if f not in body]
    if absent:
        raise ValueError("PZA/1 %s: the envelope lacks %s" % (kind, absent))
    extra = set(body) - _keyed_fields(body)
    if extra:
        raise ValueError("PZA/1 %s: unknown fields %s" % (kind, sorted(extra)))


def _keyed_fields(body):
    kind = body.get("kind")
    if kind == "event":
        return set(ORDER["event"]) | set(EVENT_FIELDS.get(body.get("event"), ()))
    return set(ORDER[kind])


def encode(kind, body, same=()):
    """One line, without its newline: positional for frame and map (`same` names the groups elided as true), keyed
    sorted JSON otherwise."""
    if kind not in KINDS:
        raise ValueError("PZA/1: unknown kind %r" % (kind,))
    if body.get("kind", kind) != kind:
        raise ValueError("PZA/1: a %s body under kind %s" % (body.get("kind"), kind))
    body = dict(body, kind=kind)
    if kind in POSITIONAL:
        bad = [g for g in same if SHAPES[kind].get(g, ("",))[0] != "group"]
        if bad:
            raise ValueError("PZA/1 %s: not groups: %s" % (kind, bad))
        return _enc(kind, body, frozenset(same))
    if same:
        raise ValueError("PZA/1 %s: a keyed line elides nothing" % kind)
    _keyed_check(body)
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _dec(owner, a, top=False):
    if a is None:
        return None
    order = _POS[owner]
    if not isinstance(a, list) or not (len(a) == len(order) or PRIOR.get(owner, len(order)) <= len(a) < len(order)):
        raise ValueError("PZA/1 %s: want %s fields, got %r" % (owner, len(order), a))
    shapes = SHAPES.get(owner, {})
    d = {}
    for f, x in zip(order, a):
        s = shapes.get(f)
        if s is None:
            d[f] = x
        elif s[0] == "group":
            d[f] = SAME if (top and x is True) else _dec(s[1], x)
        elif s[0] == "rec":
            d[f] = _dec(s[1], x)
        elif x is None:
            d[f] = None
        elif not isinstance(x, list):
            raise ValueError("PZA/1 %s.%s: not a list: %r" % (owner, f, x))
        elif s[0] == "list":
            d[f] = [_dec(s[1], e) for e in x]
        else:
            d[f] = list(x)
    for f in order[len(a):]:
        d[f] = None
    return d


def decode(obj):
    """A parsed line (a list for a positional kind, a dict for a keyed one) as its keyed dict; an elided group is
    SAME. ValueError on an unknown kind, a kind in the wrong form, a keyed line without the envelope, an unknown field
    or a wrong arity."""
    if isinstance(obj, list):
        kind = obj[0] if obj else None
        if kind not in POSITIONAL:
            raise ValueError("PZA/1: not a positional kind: %r" % (kind,))
        return _dec(kind, obj, top=True)
    if isinstance(obj, dict):
        kind = obj.get("kind")
        if kind not in KINDS or kind in POSITIONAL:
            raise ValueError("PZA/1: not a keyed kind: %r" % (kind,))
        _keyed_check(obj)
        return dict(obj)
    raise ValueError("PZA/1: not a line: %r" % (obj,))


def merge_delta(frame, base):
    """The full frame: every SAME group of `frame` taken from `base`, a full frame."""
    out = dict(frame)
    for f, s in SHAPES[out["kind"]].items():
        if s[0] == "group" and out.get(f) is SAME:
            if f not in base or base[f] is SAME:
                raise ValueError("PZA/1: the base elides %s too" % f)
            out[f] = base[f]
    return out


_ENUMS = {"gait": GAITS, "ikind": IKINDS, "filter": FILTERS}


class _Cmd:
    """A command's args() is its fields in schema order; an enum-typed field is checked on construction."""
    TYPE: ClassVar[str] = ""

    def __post_init__(self):
        for f in dataclasses.fields(self):
            allowed = _ENUMS.get(ACTION_ARGS[self.TYPE][f.name])
            if allowed is not None and getattr(self, f.name) not in allowed:
                raise ValueError("PZA/1 %s.%s: %r not in %s" % (self.TYPE, f.name, getattr(self, f.name), allowed))

    def args(self):
        return {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}
'''

PY_TYPES = {"int": "int", "float": "float", "str": "str", "gait": "str", "ikind": "str", "filter": "str"}


def _class_name(t):
    return t[0].upper() + t[1:]


def render_py(sch=None):
    sch = sch or load()
    P = [PY_HEAD.rstrip("\n"), ""]
    P.append("PROTO = %s" % _pl(sch["proto"]))
    P.append("KINDS = %s" % _pl(sch["kinds"]))
    P.append("POSITIONAL = %s" % _pl(sch["positional"]))
    P.append("ENVELOPE = %s" % _pl(ENVELOPE))
    P.extend(_pdict("ORDER", {k: sch["order"][k] for k in sch["kinds"]}, "each kind's top-level fields in order"))
    P.extend(_pdict("GROUPS", {g: d["order"] for g, d in sch["groups"].items()}, "a frame's groups, elidable in a delta"))
    P.extend(_pdict("PRIOR", {g: d["prior"] for g, d in sch["groups"].items() if d.get("prior") is not None},
                    "a group's oldest arity (before its appended fields): a shorter array of it, down to this, decodes "
                    "with the trailing fields None"))
    P.extend(_pdict("RECORDS", {r: d["order"] for r, d in sch["records"].items()}, "the positional records"))
    P.extend(_pdict("SHAPES", {o: {f: list(s) for f, s in sh.items()} for o, sh in sch["shapes"].items() if sh},
                    'each positional field that is not a plain value: ("group" | "rec" | "list" | "vlist", its name)'))
    P.append("REASONS = frozenset(%s)" % _pl(sch["reasons"]))
    P.append("ACTION_TYPES = %s" % _pl(sch["action_types"]))
    P.extend(_pdict("ACTION_ARGS", {t: {a["name"]: a["kind"] for a in sch["actions"][t]["args"]}
                                    for t in sch["action_types"]}, "each action type's arguments and their kinds"))
    P.append("GAITS = %s" % _pl(sch["gaits"]))
    P.append("IKINDS = %s" % _pl(sch["ikinds"]))
    P.append("FILTERS = %s" % _pl(sch["filters"]))
    P.append("ACT_STATES = %s" % _pl(sch["act_states"]))
    P.append("MAP_MODES = %s" % _pl(sch["map_modes"]))
    P.append("EVENT_KINDS = %s" % _pl(sch["event_kinds"]))
    P.extend(_pdict("EVENT_FIELDS", {k: sch["events"][k] for k in sch["event_kinds"]},
                    "each event kind's own fields, flat beside event and gameMin"))
    P.append(PY_RUNTIME.rstrip("\n"))
    for t in sch["action_types"]:
        a = sch["actions"][t]
        P.append("")
        P.append("")
        P.append("@dataclasses.dataclass(frozen=True)")
        P.append("class %s(_Cmd):" % _class_name(t))
        P.append('    """%s"""' % a["description"])
        P.append("    TYPE: ClassVar[str] = %s" % _pl(t))
        for arg in a["args"]:
            line = "    %s: %s" % (arg["name"], PY_TYPES[arg["kind"]])
            if arg["has_default"]:
                line += " = %s" % _pl(arg["default"])
            P.append(line + "  # " + arg["prop"]["description"])
    return "\n".join(P) + "\n"


# ---- the tool descriptions ------------------------------------------------------------------------------------

JSON_TYPES = {"int": "integer", "float": "number", "str": "string"}


def render_tools(sch=None):
    sch = sch or load()
    defs = sch["raw"]["$defs"]
    tools = []
    for t in sch["action_types"]:
        a = sch["actions"][t]
        props = {}
        for arg in a["args"]:
            if arg["kind"] in ARG_ENUMS:
                p = {"type": "string", "enum": list(defs[arg["kind"]]["enum"])}
            else:
                p = {"type": JSON_TYPES[arg["kind"]]}
            p["description"] = arg["prop"]["description"]
            if arg["has_default"]:
                p["default"] = arg["default"]
            props[arg["name"]] = p
        tools.append({"name": t, "description": a["description"],
                      "input_schema": {"type": "object", "properties": props,
                                       "required": [x["name"] for x in a["args"] if not x["has_default"]],
                                       "additionalProperties": False}})
    return json.dumps(tools, indent=2, ensure_ascii=False) + "\n"


# ---- the command line -----------------------------------------------------------------------------------------

OUTPUTS = {LUA_REL: render_lua, PY_REL: render_py, TOOLS_REL: render_tools}


def _lf(s):
    return s.replace("\r\n", "\n")


def main(argv=None, root=REPO):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 when a generated target differs from a fresh render")
    ap.add_argument("--write", action="store_true", help="regenerate the three targets")
    a = ap.parse_args(argv)
    if a.check == a.write:
        ap.error("give exactly one of --check and --write")
    sch = load()
    fresh = {rel: render(sch) for rel, render in OUTPUTS.items()}
    if a.write:
        for rel, text in fresh.items():
            path = os.path.join(root, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
            print("pza_schema: wrote %s" % rel)
        return 0
    drift = False
    for rel, text in fresh.items():
        try:
            with open(os.path.join(root, *rel.split("/")), encoding="utf-8", newline="") as fh:
                cur = fh.read()
        except OSError:
            cur = None
        if cur is None or _lf(cur) != _lf(text):
            print("pza_schema: %s differs" % rel)
            drift = True
    if drift:
        print("pza_schema: out of sync; regenerate with --write")
        return 1
    print("pza_schema: in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
