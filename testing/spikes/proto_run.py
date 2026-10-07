r"""Plan 10c Task H1: offline prototypes against the golden trace (review-mod-architecture E1's offline half, E2,
E3 and E4), in lupa (C Lua 5.1: relative shares, never Kahlua milliseconds).

The trees. A variant is the mod's Lua at the pinned base (mod/NutritionRevamp/common/media/lua at 9578eb9, every
shared/ and server/ file's sha256 over its LF-normalised text in proto/BASE.sha256; a moved mod/ file stops the
run) with the variant's overlay: proto/<variant>/{shared,server}/<file> replaces the base file of that name. Each
overlay file is a whole copy of its base file with the one change and PROTO comments; nothing under mod/ is
touched. Variants:
  - base: no overlay (the unmodified copy; the baseline).
  - heal1: E2 as the plan words it -- heal once, after the step: the pre-step heals of Nutrients, Metabolism and
    Effects removed (Strength's single heal kept), the Nutrients key prefixes built lazily.
  - heal1pre: E2's other placement -- heal once, before the step: the post-step heals removed instead, the same
    lazy prefixes.
  - hoist: E3 -- the per-record dial exponent cached across minutes, the ladder read once per record, one
    exp(-dtD) a pass handed to the excess ladder.
  - slowK: E4 -- the 27 nutrient records (K.nutrients.minute, the excess ladder inside it) and the effects
    rebuild run every K game minutes in a per-player slot (hash(username) mod K), the absorbed and ingested
    amounts and dtM summed between slow steps; K is the env global NR_PROTO_SLOWK.
The loader replaces server_host._load (the host and the golden module are imported, never edited): each file the
host loads is read from the variant's tree, and the profile's probes (below) are spliced into the text in memory.

The scenario is golden_trace.run's loop, repeated here with two hooks (an injection before the minute's
EveryOneMinute, a reader after its ticks); with no hooks it serialises byte for byte to the golden.

The profiler. NR_PROF.b(id) / NR_PROF.e(id) probes, spliced as whole lines around named blocks (ANCHORS) and
around each pipeline step in NR_Server_Minute.run, read a high-resolution clock injected from Python
(time.perf_counter; os.clock is 1 ms on this Windows host). A stack gives each id its inclusive and exclusive
time; the cost of a probe pair is calibrated in the same runtime and subtracted from every enclosing block
(c_pair per nested pair from inclusive times, c_out per direct child from exclusive times). The fine pass also
wraps the record engine's kernel functions at run time. Shares are of the step and of the pipeline
(NR.server.minute.run), summed over REPS scenario runs.

    python testing/spikes/proto_run.py            everything: out/proto-results.json and out/proto-summary.md
    python testing/spikes/proto_run.py --pin      rewrite proto/BASE.sha256 from mod/ (only when re-cutting)
    python testing/spikes/proto_run.py --digest   each variant's trace sha256, twice (the determinism check)
"""
import hashlib
import json
import math
import os
import re
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
KERNEL_TESTS = os.path.join(REPO, "testing", "tests", "kernel")
for p in (KERNEL_TESTS, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import golden_trace as G  # noqa: E402
import server_host as SH  # noqa: E402
import coarse_minute as CM  # noqa: E402

MOD_LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
PROTO = os.path.join(HERE, "proto")
PIN = os.path.join(PROTO, "BASE.sha256")
OUT = os.path.join(HERE, "out")
BASE_COMMIT = "9578eb9"
VARIANTS = ("base", "heal1", "heal1pre", "hoist", "slowK")
KS = (5, 10, 30, 60)
REPS = 20              # scenario runs per profile
TIMING_REPS = 40       # interleaved scenario runs per variant for the pipeline-only timing
INJECT_MINUTE = 75     # the mutation pass's injection minute (after the minute-70 meals, before the day close at 90)
INJECT_PLAYER = "g1"


# --- the trees ---------------------------------------------------------------------------------------------

def _text(path):
    with open(path, encoding="utf-8") as fh:          # universal newlines: a CRLF checkout reads as LF
        return fh.read()


def _sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _mod_files():
    out = []
    for sub in ("shared", "server"):
        d = os.path.join(MOD_LUA, sub)
        for name in sorted(os.listdir(d)):
            if name.endswith(".lua"):
                out.append(sub + "/" + name)
    return out


def write_pin():
    lines = ["# mod/NutritionRevamp/common/media/lua at %s: sha256 of each file's LF-normalised text" % BASE_COMMIT]
    for rel in _mod_files():
        lines.append("%s  %s" % (_sha_text(_text(os.path.join(MOD_LUA, rel))), rel))
    with open(PIN, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    return len(lines) - 1


def read_pin():
    pins = {}
    for line in _text(PIN).splitlines():
        if line.startswith("#") or not line.strip():
            continue
        sha, rel = line.split("  ", 1)
        pins[rel] = sha
    return pins


class Tree:
    """A variant's tree: the pinned base plus the overlay, with optional in-memory edits (probes, mutations)."""

    def __init__(self, variant, probes=None, edits=None):
        if variant not in VARIANTS:
            raise ValueError(variant)
        self.variant = variant
        self.probes = probes          # None, "pipeline" (the pipeline timer only), "coarse" or "fine"
        self.edits = edits or []      # [(basename, old, new)], each applied exactly once
        self.pins = read_pin()
        self.applied = set()
        self.missing = set()

    def overlay(self, rel):
        if self.variant == "base":
            return None
        p = os.path.join(PROTO, self.variant, rel.replace("/", os.sep))
        return p if os.path.exists(p) else None

    def source(self, path):
        sub = os.path.basename(os.path.dirname(path))
        name = os.path.basename(path)
        rel = sub + "/" + name
        base = _text(path)
        if self.pins.get(rel) != _sha_text(base):
            raise RuntimeError("mod/ moved since the proto was cut (%s at %s): re-cut the overlays" % (rel, BASE_COMMIT))
        ov = self.overlay(rel)
        src = _text(ov) if ov else base
        for (fn, old, new) in self.edits:
            if fn == name:
                if src.count(old) != 1:
                    raise RuntimeError("edit anchor not unique in %s: %r" % (name, old[:60]))
                src = src.replace(old, new)
        if self.probes:
            src = splice(src, name, self.probes, self.applied, self.missing)
        return src

    def overlay_files(self):
        if self.variant == "base":
            return {}
        out = {}
        root = os.path.join(PROTO, self.variant)
        for sub in ("shared", "server"):
            d = os.path.join(root, sub)
            if os.path.isdir(d):
                for name in sorted(os.listdir(d)):
                    out[sub + "/" + name] = _sha_text(_text(os.path.join(d, name)))
        return out


CURRENT = {"tree": None}


def _load(rt, path):
    src = CURRENT["tree"].source(path)
    rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@" + os.path.basename(path))()


SH._load = _load      # the host's loader, replaced in this process only (server_host.py is not edited)


# --- the profiler ------------------------------------------------------------------------------------------

PROF_ENV = r"""
NR_PROF = { on = false, sp = 0, ids = {}, st = {}, ch = {}, np = {}, nd = {},
            incl = {}, excl = {}, cnt = {}, inner = {}, direct = {}, unwound = 0, orphan = 0, sid = {} }
for _, n in ipairs({ "bus", "fast", "reconcile", "kinetics", "metabolism", "nutrients", "effects", "strength",
                     "weight" }) do
    NR_PROF.sid[n] = n
end
NR_PROF.b = function(id)
    local P = NR_PROF
    if not P.on then return end
    local sp = P.sp + 1
    P.sp = sp
    P.ids[sp] = id
    P.ch[sp] = 0
    P.np[sp] = 0
    P.nd[sp] = 0
    P.st[sp] = NR_PROF_CLOCK()
end
NR_PROF.e = function(id)
    local P = NR_PROF
    if not P.on then return end
    local t = NR_PROF_CLOCK()
    local sp = P.sp
    while sp > 0 and P.ids[sp] ~= id do sp = sp - 1; P.unwound = P.unwound + 1 end
    if sp == 0 then P.orphan = P.orphan + 1; return end
    local incl = t - P.st[sp]
    P.incl[id] = (P.incl[id] or 0) + incl
    P.excl[id] = (P.excl[id] or 0) + incl - P.ch[sp]
    P.cnt[id] = (P.cnt[id] or 0) + 1
    P.inner[id] = (P.inner[id] or 0) + P.np[sp]
    P.direct[id] = (P.direct[id] or 0) + P.nd[sp]
    P.sp = sp - 1
    if sp > 1 then
        P.ch[sp - 1] = P.ch[sp - 1] + incl
        P.np[sp - 1] = P.np[sp - 1] + P.np[sp] + 1
        P.nd[sp - 1] = P.nd[sp - 1] + 1
    end
end
NR_PROF.reset = function()
    local P = NR_PROF
    P.sp = 0; P.incl = {}; P.excl = {}; P.cnt = {}; P.inner = {}; P.direct = {}; P.unwound = 0; P.orphan = 0
end
-- The calibration: n empty pairs inside one enclosing pair. c_in is an empty pair's own inclusive time; c_pair
-- what one nested pair adds to its enclosing block's inclusive time.
NR_PROF.calibrate = function(n)
    local P = NR_PROF
    P.reset()
    P.on = true
    P.b("cal")
    for i = 1, n do
        P.b("x")
        P.e("x")
    end
    P.e("cal")
    local tl0 = NR_PROF_CLOCK()
    for i = 1, n do end
    local loop = NR_PROF_CLOCK() - tl0
    P.on = false
    local cPair = (P.incl["cal"] - loop) / n
    local cIn = P.incl["x"] / n
    P.reset()
    return cPair, cIn
end
-- The fine pass: the record engine's kernel functions wrapped at run time (looked up at call time, so a wrapper
-- installed after load is the one called).
NR_PROF.wrapFine = function()
    local K = NutritionRevamp.kernel
    local function wrap(tbl, name, id)
        local f = tbl[name]
        tbl[name] = function(...)
            NR_PROF.b(id)
            local a, b, c, d = f(...)
            NR_PROF.e(id)
            return a, b, c, d
        end
    end
    for _, n in ipairs({ "requirement", "kEff", "dialExp", "stepPool", "cap", "excess", "gradeHyst", "gradeTwo",
                         "ladderOf", "allRepleteOf", "anaemic", "gradeOf" }) do
        wrap(K.nutrients, n, "records/" .. n)
    end
    wrap(K.interact, "two", "records/two")
    wrap(K.effects, "compose", "effects/rebuild/compose")
    wrap(K.effects, "changed", "effects/rebuild/changed")
    wrap(K.heal, "body", "heal.body")
end
"""

# Probes: (file, start marker, end marker, id). The block spliced is the whole lines from the start marker's line
# through the line holding the first end marker after it (end None: the start marker's own lines). A marker
# absent from a variant (a heal the variant removed) is skipped and listed. Ids name their place: "pipeline" is
# NR.server.minute.run, "<step>" a pipeline step, "<step>/<block>" a block inside it.
ANCHORS = [
    # the walk and the drain
    ("NR_Server_Players.lua", "        P.work(username, player)", None, "work"),
    ("NR_Server_Players.lua", "    NR.server.minute.run(username, player, r)", None, "pipeline"),
    # nutrients
    ("NR_Server_Nutrients.lua", "    ensure(record, body, ageH)\n", None, "nutrients/ensure"),
    ("NR_Server_Nutrients.lua", "    heal(username, record, body, ageH)\n    local n, f, a", "ageH)", "nutrients/heal.pre"),
    ("NR_Server_Nutrients.lua", "    local alcDose, cafDose = K.acute.absorbGut(a, dtH)",
     "    cafDose = cafDose + (absorbed.caffeine or 0)", "nutrients/gut"),
    ("NR_Server_Nutrients.lua", "    if body.dayIndex > n.lastDayIndex then closeDay(record, body, w, ageH) end", None,
     "nutrients/closeDay"),
    ("NR_Server_Nutrients.lua", "    factors(absorbed, ingested, n, body.lm, caMeal, cafDose, alcDose)", None,
     "nutrients/factors"),
    ("NR_Server_Nutrients.lua", "    local hSince = ageH - body.lastCloseAgeH",
     "    if n.zinc ~= nil then ctx.e24Zn = n.zinc.e24 end", "nutrients/ctx"),
    ("NR_Server_Nutrients.lua", "    K.nutrients.minute(n, NR.data.records, absorbed, ingested, ctx, dtM)", None,
     "nutrients/records"),
    ("NR_Server_Nutrients.lua", "    local kSlow = NUT.slowK()", "    NUT.slowDueNow = math.fmod(", "nutrients/slowAcc"),
    ("NR_Server_Nutrients.lua", "        K.nutrients.minute(n, NR.data.records, acc.abs, acc.ing, ctx, acc.dt)", None,
     "nutrients/records"),
    ("NR_Server_Nutrients.lua", "    -- the fluids\n", "    f.sweatActive = K.fluids.sweatActive(f)", "nutrients/fluids"),
    ("NR_Server_Nutrients.lua", "    -- the acute states\n", "    K.acute.iu(a, f.dehydPct, n.ironGrade)", "nutrients/acute"),
    ("NR_Server_Nutrients.lua", "    heal(username, record, body, ageH)\n    NUT.stats.players", "ageH)", "nutrients/heal.post"),
    # metabolism
    ("NR_Server_Metabolism.lua", "    local body = MET.ensureBody(username, player, record, ageH)", None,
     "metabolism/ensureBody"),
    ("NR_Server_Metabolism.lua", "    heal(username, body, ageH, player)\n    local dtM", "player)", "metabolism/heal.pre"),
    ("NR_Server_Metabolism.lua", "        K.energy.intake(body, handoff, dtM)", None, "metabolism/intake"),
    ("NR_Server_Metabolism.lua", "    local className, moving, modifier, loadKg,", "= MET.readActivity(player, ageH)",
     "metabolism/readActivity"),
    ("NR_Server_Metabolism.lua", "    local met = K.energy.activityMet(", "    K.energy.minute(body, met, not moving,",
     "metabolism/energy"),
    ("NR_Server_Metabolism.lua", "    K.training.sample(body,", "    K.strength.neuralStep(body,", "metabolism/training"),
    ("NR_Server_Metabolism.lua", "    local ironGrade, allReplete, dehydPct, g, awakeH, debtH, cafEffect, cafTol = nutrientInputs(",
     None, "metabolism/inputs"),
    ("NR_Server_Metabolism.lua", "    local today = math.floor(ageH / 24)\n    local closes = 0",
     "        body.dayIndex = today\n    end", "metabolism/closeDay"),
    ("NR_Server_Metabolism.lua", "    w = body.fm + body.lm\n    local fatDep = 0", "    body.lastAgeH = ageH",
     "metabolism/scalars"),
    ("NR_Server_Metabolism.lua", "    heal(username, body, ageH, player)\nend\n\n-- One player's minute", "player)",
     "metabolism/heal.post"),
    # effects
    ("NR_Server_Effects.lua", "    local E = record.effects\n    if type(E) ~= \"table\" then",
     "ea waits for a seen close\n    end", "effects/ensure"),
    ("NR_Server_Effects.lua", "    addFields(E, body)\n    heal(username, E, body)", "    heal(username, E, body)",
     "effects/heal.pre"),
    ("NR_Server_Effects.lua", "    if body.dayIndex ~= E.lastDay then",
     "    if finite(body.exKcalDay) then E.exSeen = body.exKcalDay end", "effects/closeDay"),
    ("NR_Server_Effects.lua", "    -- 2. the bands and the flags", "+ (F.coldCredit and 10000 or 0) + (F.boutVig and 100000 or 0)",
     "effects/bands"),
    ("NR_Server_Effects.lua", "    local rebuilt = false", "        EFF.stats.rebuilds = EFF.stats.rebuilds + 1\n    end",
     "effects/rebuild"),
    ("NR_Server_Effects.lua", "    E.fOff = K.effects.fOff(", "        E.tempTarget = setPoint + adj\n    end", "effects/scalars"),
    ("NR_Server_Effects.lua", "    local changedTraits = traits(player, record, body, E, nut, sev, dtM / 1440)", None,
     "effects/traits"),
    ("NR_Server_Effects.lua", "    local d = K.effects.drain(", None, "effects/drain"),
    ("NR_Server_Effects.lua", "    if record.dead == true then\n        EFF.stats.skippedDead",
     "            EFF.stats.drainMinutes = EFF.stats.drainMinutes + 1\n        end\n    end", "effects/bodyWrites"),
    ("NR_Server_Effects.lua", "    heal(username, E, body)\nend", "body)", "effects/heal.post"),
    # strength
    ("NR_Server_Strength.lua", "    heal(username, body, ageH)\n    local dtH", "ageH)", "strength/heal"),
    ("NR_Server_Strength.lua", "    local perk = Perks ~= nil and Perks.Strength or nil\n    if perk ~= nil then\n        local lvanilla",
     "                STR.stats.bandRepairs = STR.stats.bandRepairs + 1   -- #2740: the band set re-asserted\n            end\n        end\n    end",
     "strength/perk"),
    ("NR_Server_Strength.lua", "    carry(player, record, body, ageH)\nend", "ageH)", "strength/carry"),
]
STEP_LINE = "            local ok, err = pcall(fn, username, player, record, ctx)"
HEAL_IDS = ("nutrients/heal.pre", "nutrients/heal.post", "metabolism/heal.pre", "metabolism/heal.post",
            "effects/heal.pre", "effects/heal.post", "strength/heal")
STEPS = ("bus", "fast", "reconcile", "kinetics", "metabolism", "nutrients", "effects", "strength", "weight")


def _block(src, start, end):
    """(i, j): the whole lines from start's line through the line holding the first `end` at or after start."""
    if src.count(start) != 1:
        return None
    s0 = src.index(start)
    i = src.rfind("\n", 0, s0) + 1
    if end is None:
        k = s0 + len(start)
    else:
        k = src.find(end, s0)
        if k < 0:
            return None
        k += len(end)
    j = src.find("\n", k - 1)
    if j < 0:
        j = len(src) - 1
    return i, j + 1


def splice(src, name, mode, applied, missing):
    if mode in ("pipeline", "coarse", "fine"):
        pass
    else:
        raise ValueError(mode)
    anchors = [a for a in ANCHORS if a[0] == name]
    if mode == "pipeline":
        anchors = [a for a in anchors if a[3] == "pipeline"]
    else:
        if name == "NR_Server_Minute.lua":
            if src.count(STEP_LINE) != 1:
                raise RuntimeError("the step line moved")
            src = src.replace(STEP_LINE, "NR_PROF.b(NR_PROF.sid[MIN.ORDER[i]])\n" + STEP_LINE +
                              "\nNR_PROF.e(NR_PROF.sid[MIN.ORDER[i]])")
            applied.add("<steps>")
    # splice from the end of the text backwards so earlier offsets stay valid
    found = []
    for (_, start, end, pid) in anchors:
        blk = _block(src, start, end)
        if blk is None:
            missing.add(pid)
            continue
        found.append((blk, pid))
    found.sort(key=lambda t: -t[0][0])
    for a, b in zip(sorted(f[0] for f in found), sorted(f[0] for f in found)[1:]):
        if b[0] < a[1]:
            raise RuntimeError("overlapping probe blocks in %s" % name)
    for (i, j), pid in found:
        body = src[i:j]
        src = src[:i] + 'NR_PROF.b("%s")\n' % pid + body + 'NR_PROF.e("%s")\n' % pid + src[j:]
        applied.add(pid)
    missing.difference_update(applied)
    return src


# --- the host and the scenario -----------------------------------------------------------------------------

def new_host(tree, slowk=None, rebuild=True):
    CURRENT["tree"] = tree
    env = G.ENV + PROF_ENV
    if slowk is not None:
        env += "\nNR_PROTO_SLOWK = %d\n" % slowk
    if not rebuild:
        env += "\nNR_PROTO_SLOWK_REBUILD = false\n"
    h = SH.Host(extra_env=env)
    h.G.NR_PROF_CLOCK = time.perf_counter
    if tree.probes == "fine":
        h.G.NR_PROF.wrapFine()
    return h


def scenario(h, inject=None, after=None, golden_nan=True):
    """golden_trace.run's loop, with an injection before each minute's EveryOneMinute and a reader after its ticks.
    golden_nan=False drops the golden's own minute-115 NaN (the mutation pass isolates its own injections)."""
    players = {n: G._new_player(h, n, G.MACROS[n]) for n in G.NAMES}
    order = list(G.NAMES)

    def publish():
        h.online(*[players[n] for n in order])

    publish()
    h.T.age = G.START_AGE
    snapshots = []
    for m in range(1, G.MINUTES + 1):
        h.T.age = G.START_AGE + m / 60.0
        h.T.m = m
        h.T.engine()
        if m in G.MEAL_MINUTES:
            for n in order:
                G._meal(h, m, n)
        if m == 45:
            nut = players["g6"].nut
            nut.cal = nut.cal + G.STORE_RAISE_G6[0]
            nut.carb = nut.carb + G.STORE_RAISE_G6[1]
            nut.lip = nut.lip + G.STORE_RAISE_G6[2]
            nut.pro = nut.pro + G.STORE_RAISE_G6[3]
        if m == 50:
            G._fluid(h, "g1", "Wine", G.DRINK_LITRES)
            G._fluid(h, "g5", "Tea", G.DRINK_LITRES)
        if m == 60:
            G._fluid(h, "g2", "Water", G.DRINK_LITRES)
        if m == 100:
            players["g3"].deadFlag = True
        if m == 101:
            players["g3"] = G._new_player(h, "g3", G.RESPAWN_G3)
            publish()
            h.fire("OnNewGame", players["g3"], None)
        if m == 115 and golden_nan:
            body = h.record("g2")["body"]
            body["at"] = float("nan")
            body["inDay"] = float("nan")
        if m == 150:
            order.remove("g4")
            publish()
        if m == 180:
            players["g4"] = G._new_player(h, "g4", G.RETURN_G4)
            order.insert(3, "g4")
            publish()
        if m == 200:
            h.fire("OnClientCommand", "NutritionRevamp", "mirror.request", players["g5"], None)
        if inject is not None:
            inject(m, h, players)
        h.minute()
        h.tick(G.TICKS)
        if after is not None:
            after(m, h, players)
        if m % G.SNAPSHOT_EVERY == 0:
            snapshots.append(G._snapshot(h, m, players))
    return {"snapshots": snapshots, "printed_count": len(h.printed())}


def trace_text(tree, slowk=None, inject=None, after=None, keep_host=False, lua=None, golden_nan=True, rebuild=True):
    h = new_host(tree, slowk, rebuild)
    if lua is not None:
        h.rt.execute(lua)
    text = G.serialize(scenario(h, inject, after, golden_nan))
    return (text, h) if keep_host else text


def golden_text():
    with open(G.GOLDEN, encoding="utf-8", newline="") as fh:
        return fh.read()


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def first_diff(a, b):
    """The first differing line of two serialised traces: its snapshot minute and the path of keys above it."""
    la, lb = a.split("\n"), b.split("\n")
    for i in range(min(len(la), len(lb))):
        if la[i] != lb[i]:
            path = []
            depth = len(la[i]) - len(la[i].lstrip(" "))
            minute = None
            for j in range(i, -1, -1):
                ln = la[j]
                d = len(ln) - len(ln.lstrip(" "))
                st = ln.strip()
                if minute is None and d == 3 and st.startswith('"minute":'):
                    minute = st.split(":")[1].strip().rstrip(",")
                if d < depth and st.endswith("{"):
                    if ":" in st:
                        path.append(st.split(":")[0].strip('"'))
                    depth = d
            return {"line": i + 1, "minute": minute, "path": "/".join(reversed(path)),
                    "golden": la[i].strip(), "variant": lb[i].strip()}
    if len(la) != len(lb):
        return {"line": min(len(la), len(lb)) + 1, "minute": None, "path": "<length>", "golden": len(la),
                "variant": len(lb)}
    return None


# --- the profiles -----------------------------------------------------------------------------------------

def profile(variant, mode, reps, slowk=None):
    """reps scenario runs with the probes on; the totals, the calibration and the corrected figures."""
    tree = Tree(variant, probes=mode)
    totals = {"incl": {}, "excl": {}, "cnt": {}, "inner": {}, "direct": {}}
    cal = []
    unwound = orphan = 0
    traces = set()
    for r in range(reps):
        h = new_host(tree, slowk)
        P = h.G.NR_PROF
        cal.append(tuple(P.calibrate(20000)))
        P.reset()
        P.on = True
        tr = scenario(h)
        P.on = False
        if r < 2:
            traces.add(_sha(G.serialize(tr)))
        for k in totals:
            for key, v in P[k].items():
                totals[k][key] = totals[k].get(key, 0) + v
        unwound += P.unwound
        orphan += P.orphan
    c_pair = statistics.median(c[0] for c in cal)
    c_in = statistics.median(c[1] for c in cal)
    c_out = c_pair - c_in
    ids = sorted(totals["incl"])
    corr = {}
    for i in ids:
        # a block's own probe pair adds c_in to each of its instances; each nested pair adds c_pair to its
        # inclusive time and each direct child c_out to its exclusive time
        own = c_in * totals["cnt"][i]
        incl = totals["incl"][i] - own - c_pair * totals["inner"].get(i, 0)
        excl = totals["excl"][i] - own - c_out * totals["direct"].get(i, 0)
        corr[i] = {"incl_s": incl, "excl_s": excl, "count": int(totals["cnt"][i]),
                   "inner_pairs": int(totals["inner"].get(i, 0))}
    pipe = corr.get("pipeline", {}).get("incl_s") or float("nan")
    runs = corr.get("pipeline", {}).get("count") or 0
    for i in ids:
        c = corr[i]
        step = i.split("/", 1)[0]
        c["us_per_pipeline_run"] = c["incl_s"] / runs * 1e6 if runs else float("nan")
        c["share_pipeline"] = c["incl_s"] / pipe
        c["excl_share_pipeline"] = c["excl_s"] / pipe
        if "/" in i and step in corr:
            c["share_step"] = c["incl_s"] / corr[step]["incl_s"]
    return {"variant": variant, "mode": mode, "reps": reps, "slowk": slowk, "pipeline_runs": runs,
            "c_pair_us": c_pair * 1e6, "c_in_us": c_in * 1e6, "unwound": unwound, "orphan": orphan,
            "applied": sorted(tree.applied), "missing": sorted(tree.missing), "trace_sha256": sorted(traces),
            "blocks": corr}


def timing(variants, reps, slowks=None):
    """The pipeline alone timed (one probe pair a run), the variants' scenario runs interleaved."""
    per = {v: [] for v in variants}
    for r in range(reps):
        for v in variants:
            name, k = v if isinstance(v, tuple) else (v, None)
            tree = Tree(name, probes="pipeline")
            h = new_host(tree, k)
            P = h.G.NR_PROF
            c_pair, c_in = P.calibrate(20000)
            P.reset()
            P.on = True
            scenario(h)
            P.on = False
            n = P.cnt["pipeline"]
            per[v].append((P.incl["pipeline"] - c_in * n) / n * 1e6)
    out = {}
    base = per[variants[0]]
    for v, xs in per.items():
        key = v if isinstance(v, str) else "%s@K=%d" % v
        ratios = sorted(x / b for x, b in zip(xs, base))
        q = len(ratios) // 4
        out[key] = {"median_us": statistics.median(xs), "mean_us": statistics.mean(xs),
                    "sd_us": statistics.stdev(xs) if len(xs) > 1 else 0.0, "reps": len(xs),
                    "paired_ratio_median": statistics.median(ratios),
                    "paired_ratio_q1": ratios[q], "paired_ratio_q3": ratios[len(ratios) - 1 - q]}
    return out


# --- the mutation pass (heal) -----------------------------------------------------------------------------

def _nan():
    return float("nan")


def _set(path):
    """An injector: set the dotted record path (from the injected player's record) to NaN at INJECT_MINUTE."""
    parts = path.split(".")

    def inject(m, h, players):
        if m != INJECT_MINUTE:
            return
        t = h.record(INJECT_PLAYER)
        for p in parts[:-1]:
            t = t[int(p)] if p.isdigit() else t[p]
        last = parts[-1]
        if last.isdigit():
            t[int(last)] = _nan()
        else:
            t[last] = _nan()
    return inject


# (adapter, record path, what the heal guards)
INJECTIONS = [
    ("nutrients", "nutrients.vitC.p", "a nutrient key's pool"),
    ("nutrients", "nutrients.vitA.ax", "a nutrient key's acute flag (Intake writes ax and axr outside the pipeline)"),
    ("nutrients", "nutrients.epoch", "the nutrients sub-table's own field"),
    ("nutrients", "nutrients.lastAgeH", "an age field (heals to the world age)"),
    ("nutrients", "fluids.water", "the water pool"),
    ("nutrients", "acute.bac", "an acute state"),
    ("nutrients", "acute.winStartH", "an acute age field"),
    ("metabolism", "body.fm", "the fat mass"),
    ("metabolism", "body.at", "adaptive thermogenesis (the golden's own minute-115 field)"),
    ("metabolism", "body.inDay", "a day accumulator"),
    ("metabolism", "body.eb7.3", "a ring slot"),
    ("metabolism", "body.dayIndex", "the day index"),
    ("metabolism", "body.lastAgeH", "the body's age"),
    ("effects", "effects.mAcc", "a per-minute scalar"),
    ("effects", "effects.panicTarget", "a composed target"),
    ("effects", "effects.key.ep", "the rebuild key's epoch"),
    ("effects", "effects.key.b.9", "a rebuild key band slot"),
    ("strength", "body.strAgeH", "Strength's own stamp (its one heal, unchanged in every variant: a control)"),
]

# The mutants: each removes the one heal a variant keeps in one adapter (Plan 10's oracle mutation pass).
MUTANTS = {
    "heal1": {
        "nutrients": ("NR_Server_Nutrients.lua", "    heal(username, record, body, ageH)\n    NUT.stats.players",
                      "    NUT.stats.players"),
        "metabolism": ("NR_Server_Metabolism.lua", "    body.lastAgeH = ageH\n    heal(username, body, ageH, player)\nend",
                       "    body.lastAgeH = ageH\nend"),
        "effects": ("NR_Server_Effects.lua", "    -- 12. the stamps, every one finite\n    heal(username, E, body)",
                    "    -- 12. the stamps, every one finite"),
    },
    "heal1pre": {
        "nutrients": ("NR_Server_Nutrients.lua", "    ensure(record, body, ageH)\n    heal(username, record, body, ageH)",
                      "    ensure(record, body, ageH)"),
        "metabolism": ("NR_Server_Metabolism.lua",
                       "    local body = MET.ensureBody(username, player, record, ageH)\n    heal(username, body, ageH, player)",
                       "    local body = MET.ensureBody(username, player, record, ageH)"),
        "effects": ("NR_Server_Effects.lua", "    addFields(E, body)\n    heal(username, E, body)", "    addFields(E, body)"),
    },
}


def _nonfinite(h, name):
    """The dotted paths of every non-finite number in a player's record (a Lua walk)."""
    bad = []

    def rec(v, path, depth):
        if depth > 8:
            return
        if isinstance(v, float) and not math.isfinite(v):
            bad.append(path)
        elif G.lua51.lua_type(v) == "table":
            for k, x in v.items():
                rec(x, path + "." + str(k) if path else str(k), depth + 1)
    rec(h.record(name), "", 0)
    return bad


# Arithmetic NaNs: a NaN the step's own arithmetic leaves, made by wrapping the kernel call that runs just before
# the step's post heal (the class the post-step heals guard). Each fires for INJECT_PLAYER at INJECT_MINUTE only.
MID_LUA = r"""
local K = NutritionRevamp.kernel
local function mine(t, field)
    local r = NutritionRevamp.server.store.records["%(player)s"]
    return NR_T.m == %(minute)d and r ~= nil and r[field] == t
end
local tbl, name, field, set = %(tbl)s, "%(fn)s", "%(field)s", "%(set)s"
local f = tbl[name]
tbl[name] = function(t, ...)
    local a, b, c, d = f(t, ...)
    if mine(t, field) then
        local x, path = t, {}
        for p in string.gmatch(set, "[^.]+") do path[#path + 1] = p end
        for i = 1, #path - 1 do x = x[tonumber(path[i]) or path[i]] end
        x[tonumber(path[#path]) or path[#path]] = 0 / 0
    end
    return a, b, c, d
end
"""

# (adapter, the kernel call it follows, its first argument's record field, the field set NaN, what it stands for)
MID_INJECTIONS = [
    ("metabolism", "K.energy", "minute", "body", "fm", "the fat mass, NaN out of the energy step"),
    ("metabolism", "K.energy", "minute", "body", "at", "adaptive thermogenesis, NaN out of the energy step"),
    ("nutrients", "K.acute", "iu", "acute", "bac", "an acute state, NaN out of the acute block"),
    ("nutrients", "K.acute", "iu", "acute", "S", "the acute satiety-like state S, NaN out of the acute block"),
    ("effects", "K.effects", "drain", "effects", "panicTarget", "a composed target, NaN out of the drain"),
    ("effects", "K.effects", "drain", "effects", "mAcc", "a per-minute scalar, NaN out of the drain"),
]


def _run_injected(tree, inject=None, lua=None):
    after_bad = {}

    def after(m, h, players):
        if m == INJECT_MINUTE:
            after_bad["m"] = _nonfinite(h, INJECT_PLAYER)
    text, h = trace_text(tree, inject=inject, after=after, keep_host=True, lua=lua, golden_nan=False)
    lines = [ln for ln in h.printed() if "non-finite" in ln and INJECT_PLAYER in ln]
    return text, lines, after_bad.get("m", [])


def _state_text(text):
    """The trace's state alone: every snapshot's records, players, sends, syncs and instancing, without the
    adapters' counters (stats) and the log-line count (printed_count), re-serialised the golden's way."""
    d = json.loads(text)
    d.pop("printed_count", None)
    for snap in d["snapshots"]:
        snap.pop("stats", None)
    return G.serialize(d)


def _row(adapter, label, what, inject=None, lua=None):
    base_text, base_lines, base_bad = _run_injected(Tree("base"), inject, lua)
    clean = trace_text(Tree("base"), golden_nan=False)
    row = {"adapter": adapter, "path": label, "guards": what, "base_heal_lines": base_lines,
           "base_nonfinite_after_minute": base_bad, "injection_moves_base_trace": base_text != clean,
           "variants": {}}
    base_state = _state_text(base_text)
    for v in ("heal1", "heal1pre"):
        text, lines, bad = _run_injected(Tree(v), inject, lua)
        state = _state_text(text)
        res = {"trace_equal_to_base": text == base_text, "heal_lines": lines,
               "state_equal_to_base": state == base_state,
               "heal_lines_equal_to_base": lines == base_lines, "nonfinite_after_minute": bad,
               "first_diff": None if text == base_text else first_diff(base_text, text),
               "first_state_diff": None if state == base_state else first_diff(base_state, state)}
        mut = MUTANTS[v].get(adapter)
        if mut is not None:
            mtext, mlines, mbad = _run_injected(Tree(v, edits=[mut]), inject, lua)
            res["mutant"] = {"removes": "the %s heal %s keeps" % (adapter, v),
                             "killed": (mtext != text) or (mlines != lines) or (mbad != bad),
                             "trace_differs": mtext != text, "heal_lines": mlines, "nonfinite_after_minute": mbad}
        row["variants"][v] = res
    return row


def mutation_pass():
    """Input NaNs (written into the record between minutes, the class the pre-step heals guard) and arithmetic
    NaNs (left by the step itself, the class the post-step heals guard), each against base, heal1 and heal1pre,
    with the golden's own minute-115 NaN dropped so each run carries one injection; and per variant the mutant that
    removes its remaining heal in the injected adapter."""
    out = {"input": [], "arithmetic": []}
    clean = {v: trace_text(Tree(v), golden_nan=False) for v in ("base", "heal1", "heal1pre")}
    out["no_injection_equal_to_base"] = {v: clean[v] == clean["base"] for v in ("heal1", "heal1pre")}
    for adapter, path, what in INJECTIONS:
        out["input"].append(_row(adapter, path, what, inject=_set(path)))
    for adapter, tbl, fname, field, setf, what in MID_INJECTIONS:
        lua = MID_LUA % {"player": INJECT_PLAYER, "minute": INJECT_MINUTE, "tbl": tbl, "fn": fname,
                         "field": field, "set": setf}
        out["arithmetic"].append(_row(adapter, "%s.%s after %s.%s" % (field, setf, tbl, fname), what, lua=lua))
    return out


# --- slowK: the drift and the delay of each discrete change ------------------------------------------------

GRADE_RE = re.compile(r"(/g$|/x$|/effects/key/b/|Grade$|/allReplete$|/anaemia$|/vitDClinical$|/traits/|/st/perk$"
                      r"|/nightVision$|band)")


def _nav(h, players, path):
    parts = path.split("/")
    if parts[0] == "records":
        t = h.NR.server.store.records[parts[1]]
    elif parts[0] == "players":
        p = players[parts[1]]
        t = p.st if parts[2] == "st" else p.nut
        parts = parts[1:]
    else:
        return "<n/a>"
    for c in parts[2:]:
        if t is None or G.lua51.lua_type(t) != "table":
            return "<absent>"
        v = t[c]
        if v is None:
            try:
                v = t[int(c)]
            except ValueError:
                v = None
        t = v
    if t is None:
        return "<absent>"
    if isinstance(t, (bool, str)):
        return t
    if isinstance(t, (int, float)):
        return float(t)
    return "<%s>" % G.lua51.lua_type(t)


def _series(tree, slowk, paths, rebuild=True):
    ser = {p: [] for p in paths}

    def after(m, h, players):
        for p in paths:
            ser[p].append(_nav(h, players, p))
    trace_text(tree, slowk=slowk, after=after, rebuild=rebuild)
    return ser


def _events(xs):
    ev = []
    prev = object()
    for i, v in enumerate(xs):
        if v != prev and not (isinstance(v, float) and isinstance(prev, float) and math.isnan(v) and math.isnan(prev)):
            ev.append((i + 1, v))
            prev = v
    return ev


# The minutes a player is away (g4 departs at minute 150 and returns at 180) and the run's last minute: a base
# change within K minutes before either cannot show under a K-minute slow tier, and is reported as clipped.
ABSENT = {"g4": (150, 180)}
LAST_MINUTE = G.MINUTES


def _clipped(path, minute, k):
    who = path.split("/")[1] if path.count("/") >= 1 else ""
    if minute > LAST_MINUTE - k:
        return "the run's end"
    if who in ABSENT:
        a, _ = ABSENT[who]
        if a - k <= minute < a:
            return "%s's departure at minute %d" % (who, a)
    return None


def _online_delay(path, mb, mo):
    """slowK's change minute less the base's, counted in the player's online minutes."""
    pres = _present(path.split("/")[1])
    if mb in pres and mo in pres:
        return pres.index(mo) - pres.index(mb)
    return mo - mb


def align(eb, eo, k, path):
    """The base and slowK change events matched in order: a pair matches when the value is the same and the change
    is at most k minutes early or late; a base change the slow tier could not show before a departure or the run's
    end is clipped; anything else is a flip (the first one stops the walk)."""
    i = j = 0
    matched, clipped, flip = [], [], None
    while i < len(eb) or j < len(eo):
        if i < len(eb) and j < len(eo) and eb[i][1] == eo[j][1] and abs(_online_delay(path, eb[i][0], eo[j][0])) <= k:
            matched.append((eb[i][0], eo[j][0], _online_delay(path, eb[i][0], eo[j][0])))
            i += 1
            j += 1
            continue
        if i < len(eb):
            why = _clipped(path, eb[i][0], k)
            if why is not None:
                clipped.append({"minute": eb[i][0], "value": eb[i][1], "why": why})
                i += 1
                continue
        flip = {"base": eb[i] if i < len(eb) else None, "slowK": eo[j] if j < len(eo) else None}
        break
    return {"matched": matched, "clipped": clipped, "flip": flip,
            "max_abs_delay": max([abs(x[2]) for x in matched] or [0])}


def _cmp_full(base, other):
    """coarse_minute.compare, with its full continuous list kept and each leaf's fairer-band tolerance."""
    b = CM._leaves(json.loads(G.serialize(base)))
    o = CM._leaves(json.loads(G.serialize(other)))
    res = CM.compare(base, other)
    by_path = {}
    for (m, p), v in b.items():
        by_path.setdefault(p, []).append(v)
    rng, integral, by_field = {}, {}, {}
    for p, vals in by_path.items():
        nums = [float(x) for x in vals if CM._is_num(x) and math.isfinite(x)]
        if nums:
            rng[p] = max(nums) - min(nums)
            by_field.setdefault(CM._field(p), []).extend(nums)
        integral[p] = all(CM._integral(x) for x in vals)
    frng = {f: max(v) - min(v) for f, v in by_field.items()}
    fmag = {f: max(abs(x) for x in v) for f, v in by_field.items()}
    cont = []
    for key in sorted(set(b) & set(o)):
        m, p = key
        vb, vo = b[key], o[key]
        if CM._is_telemetry(p):
            continue
        if not (CM._is_num(vb) and CM._is_num(vo)) or CM._named_discrete(p) or (integral.get(p) and CM._integral(vo)):
            continue
        if not (math.isfinite(vb) and math.isfinite(vo)):
            continue
        d = abs(vo - vb)
        f = CM._field(p)
        fr = frng.get(f, 0.0)
        tol = CM.BAND_ABS if fmag.get(f, 0.0) < CM.SMALL else CM.BAND_REL * fr
        if rng.get(p, 0.0) == 0:
            tol = max(tol, CM.BAND_ABS)
        cont.append({"minute": m, "path": p, "base": vb, "other": vo, "abs": d, "range": rng.get(p, 0.0),
                     "field_range": fr, "tol": tol, "in_fair_band": d <= tol})
    res["continuous"] = cont
    return res


def _grade_paths(trace_json):
    """Every band and grade leaf of the base trace (any snapshot), for the per-minute series."""
    paths = set()
    for snap in trace_json["snapshots"]:
        flat = {}
        CM._flatten({k: v for k, v in snap.items() if k in ("records", "players")}, "", flat)
        for p in flat:
            if GRADE_RE.search(p):
                paths.add(p)
    return sorted(paths)


def _present(who):
    """The minutes a player is online, in order (g4 is away from minute 150 to 179)."""
    a = ABSENT.get(who)
    return [m for m in range(1, G.MINUTES + 1) if a is None or not (a[0] <= m < a[1])]


def _window(who, m, k):
    """The minutes at most k ONLINE minutes from m (an absence counts no time: the slow tier cannot run then)."""
    pres = _present(who)
    if m not in pres:                    # away at m: the record is frozen at the last online minute before it
        earlier = [p for p in pres if p <= m]
        if not earlier:
            return [m]
        m = earlier[-1]
    i = pres.index(m)
    return pres[max(0, i - k):i + k + 1]


def _slowk_one(k, rebuild, base_tree, base_tr, base_json, gpaths):
    tr = scenario(new_host(Tree("slowK"), k, rebuild))
    text = G.serialize(tr)
    text2 = trace_text(Tree("slowK"), slowk=k, rebuild=rebuild)
    other_json = json.loads(text)
    cmp = _cmp_full(base_json, other_json)
    failing = [c for c in cmp["continuous"] if not c["in_fair_band"]]
    snap_discrete = {d["path"] for d in cmp["discrete"]} | {d["path"] for d in cmp["structural"]}
    paths = sorted(set(gpaths) | snap_discrete | {c["path"] for c in failing})
    bs = _series(base_tree, None, paths)
    os_ = _series(Tree("slowK"), k, paths, rebuild)
    grade, other = {}, {}
    for p in sorted(set(gpaths) | snap_discrete):
        eb, eo = _events(bs[p]), _events(os_[p])
        if eb == eo:
            continue
        a = align(eb, eo, k, p)
        a["base_events"] = eb[:14]
        a["slowK_events"] = eo[:14]
        (grade if GRADE_RE.search(p) else other)[p] = a
    flips = sorted(p for p, a in grade.items() if a["flip"] is not None)
    unexplained = []
    for c in failing:
        m, p = c["minute"], c["path"]
        o = os_[p][m - 1]
        ok = False
        for mm in _window(p.split("/")[1], m, k):
            bv = bs[p][mm - 1]
            if isinstance(bv, float) and isinstance(o, float) and abs(o - bv) <= c["tol"]:
                ok = True
                break
        c["explained_by_delay"] = ok
        if not ok:
            unexplained.append(c)
    ufields, ffields = {}, {}
    for c in unexplained:
        ufields.setdefault(CM._field(c["path"]), []).append(c)
    for c in failing:
        ffields.setdefault(CM._field(c["path"]), []).append(c)
    worst = sorted(unexplained, key=lambda c: (-(c["abs"] / c["tol"]), c["minute"], c["path"]))[:20]
    r = {
        "sha256": _sha(text), "deterministic": text == text2,
        "continuous_leaves": len(cmp["continuous"]),
        "ruling4_outside": len(cmp["failing"]), "ruling4_discrete": len(cmp["discrete"]),
        "structural": len(cmp["structural"]), "telemetry_mismatches": len(cmp["telemetry"]),
        "printed_count": tr["printed_count"], "base_printed_count": base_tr["printed_count"],
        "effects_rebuilds_m240": {"base": base_json["snapshots"][-1]["stats"]["effects"]["rebuilds"],
                                  "slowK": other_json["snapshots"][-1]["stats"]["effects"]["rebuilds"]},
        "fair_outside": len(failing), "fair_fields": {f: len(v) for f, v in sorted(ffields.items())},
        "fair_explained_by_delay": len(failing) - len(unexplained),
        "fair_unexplained": len(unexplained),
        "fair_unexplained_fields": {f: len(v) for f, v in sorted(ufields.items())},
        "fair_unexplained_worst": [{"minute": c["minute"], "path": c["path"], "base": c["base"],
                                    "other": c["other"], "abs": c["abs"], "tol": c["tol"],
                                    "field_range": c["field_range"]} for c in worst],
        "snapshot_discrete": cmp["discrete"],
        "grade_changed": grade, "other_discrete_changed": other,
        "flips": flips,
        "clipped": sorted(p for p, a in grade.items() if a["clipped"]),
        "max_grade_delay": max([a["max_abs_delay"] for a in grade.values()] or [0]),
        "telemetry_m240": [t for t in cmp["telemetry"] if t["minute"] in (240, 0)],
    }
    r["safe_grades"] = not flips and tr["printed_count"] == base_tr["printed_count"]
    r["safe_fair"] = r["safe_grades"] and not unexplained
    print("slowK K=%d rebuild=%s: fair outside %d (unexplained %d), grade paths changed %d, flips %d, safe %s/%s" % (
        k, "slow" if rebuild else "every minute", len(failing), len(unexplained), len(grade), len(flips),
        r["safe_grades"], r["safe_fair"]))
    return r


def slowk_study():
    """Each K against the base run: P2's compare (ruling 4's band, kept for the record), the fairer band, and per
    minute every band and grade leaf (and every discrete leaf that differs at a snapshot) matched change by change;
    a continuous leaf outside the fairer band is explained by the slow tier's delay when the slowK value at its
    snapshot is within the band of the base value at some minute at most K online minutes away. Two arms: the
    plan's E4 (the records and the effects rebuild on the slow tier) and a diagnostic with the rebuild check kept
    every minute (the records alone on the slow tier)."""
    base_tree = Tree("base")
    base_tr = scenario(new_host(base_tree))
    base_text = G.serialize(base_tr)
    base_json = json.loads(base_text)
    gpaths = _grade_paths(base_json)
    out = {"k1_reproduces_golden": trace_text(Tree("slowK"), slowk=1) == golden_text(),
           "k1_records_only_reproduces_golden": trace_text(Tree("slowK"), slowk=1, rebuild=False) == golden_text(),
           "grade_paths_followed": len(gpaths), "k": {}, "k_records_only": {}}
    for k in KS:
        out["k"][k] = _slowk_one(k, True, base_tree, base_tr, base_json, gpaths)
        out["k_records_only"][k] = _slowk_one(k, False, base_tree, base_tr, base_json, gpaths)
    return out


# --- the run -----------------------------------------------------------------------------------------------

def digest():
    out = {}
    for v in VARIANTS:
        ks = KS if v == "slowK" else (None,)
        for k in ks:
            a = _sha(trace_text(Tree(v), slowk=k))
            b = _sha(trace_text(Tree(v), slowk=k))
            out[v if k is None else "%s@K=%d" % (v, k)] = (a, b)
    return out


def _f(x, nd=1):
    if isinstance(x, float) and not math.isfinite(x):
        return "n/a"
    return ("%%.%df" % nd) % x


def main(argv):
    if "--pin" in argv:
        print("pinned %d files" % write_pin())
        return 0
    if "--digest" in argv:
        for k, (a, b) in digest().items():
            print("%-14s %s %s %s" % (k, a, b, "same" if a == b else "DIFFERENT"))
        return 0
    gold = golden_text()
    res = {"meta": {"base_commit": BASE_COMMIT, "golden_sha256": _sha(gold), "reps": REPS,
                    "timing_reps": TIMING_REPS, "lupa": getattr(G.lua51, "__name__", "lupa.lua51"),
                    "pin_sha256": _sha(_text(PIN)),
                    "overlays": {v: Tree(v).overlay_files() for v in VARIANTS}}}
    # 1. the traces: each variant reproduces the golden (or not), unprofiled and profiled, twice
    tr = {}
    for v in ("base", "heal1", "heal1pre", "hoist"):
        texts = [trace_text(Tree(v)) for _ in range(2)]
        ptext = trace_text(Tree(v, probes="coarse"))
        ftext = trace_text(Tree(v, probes="fine"))
        tr[v] = {"sha256": [_sha(t) for t in texts], "deterministic": texts[0] == texts[1],
                 "golden": texts[0] == gold, "coarse_probed_golden": ptext == texts[0],
                 "fine_probed_golden": ftext == texts[0],
                 "first_diff": first_diff(gold, texts[0]) if texts[0] != gold else None}
        print("trace %-9s golden=%s deterministic=%s probed=%s/%s" % (
            v, tr[v]["golden"], tr[v]["deterministic"], tr[v]["coarse_probed_golden"], tr[v]["fine_probed_golden"]))
    res["traces"] = tr
    if not tr["base"]["golden"]:
        print("the base copy does not reproduce the golden: the loader is wrong", file=sys.stderr)
        return 1
    # 2. the profiles
    prof = {}
    for v in ("base", "heal1", "heal1pre", "hoist"):
        prof[v] = {"coarse": profile(v, "coarse", REPS)}
        print("profile %-9s coarse: %d runs, c_pair %.3f us" % (v, prof[v]["coarse"]["pipeline_runs"],
                                                                  prof[v]["coarse"]["c_pair_us"]))
    prof["base"]["fine"] = profile("base", "fine", REPS)
    prof["base"]["coarse_repeat"] = profile("base", "coarse", REPS)
    for k in KS:
        prof["slowK@K=%d" % k] = {"coarse": profile("slowK", "coarse", REPS, slowk=k)}
    res["profiles"] = prof
    # 3. the pipeline-only timing, interleaved
    res["timing"] = timing(["base", "heal1", "heal1pre", "hoist"] + [("slowK", k) for k in KS], TIMING_REPS)
    print("timing done")
    # 4. the mutation pass
    res["mutation"] = mutation_pass()
    print("mutation pass done")
    # 5. slowK
    res["slowK"] = slowk_study()
    print("slowK done")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "proto-results.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, indent=1, sort_keys=True, default=str)
        fh.write("\n")
    with open(os.path.join(OUT, "proto-summary.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(summary_md(res))
    return 0


def _top(blocks, n=None, key="share_pipeline"):
    rows = [(i, b) for i, b in blocks.items() if "/" in i and not i.startswith("records/")
            and i.count("/") == 1]
    rows.sort(key=lambda t: -t[1].get(key, 0))
    return rows[:n] if n else rows


def _kv(d, k):
    return d[k] if k in d else d[str(k)]


def _ratio(t):
    return "%s %% (IQR %s to %s)" % (_f(100 * (1 - t["paired_ratio_median"])), _f(100 * (1 - t["paired_ratio_q3"])),
                                     _f(100 * (1 - t["paired_ratio_q1"])))


def summary_md(res):
    L = []
    m = res["meta"]
    L.append("# H1: offline prototypes against the golden trace (heal once, hoisted constants, a slow tier)")
    L.append("")
    L.append("Generated by `testing/spikes/proto_run.py` (Plan 10c Task H1; review-mod-architecture E1's offline half, "
             "E2, E3, E4). lupa runs C Lua 5.1, not Kahlua: every figure is a share or a ratio of C-Lua time, "
             "never a server millisecond. Base: `mod/` at %s, pinned by `proto/BASE.sha256` (sha256 `%s`); the "
             "golden is `trace-1.0.0.json` (sha256 `%s`). The scenario is the golden's: six players, 240 game "
             "minutes, about 1410 pipeline runs a scenario. Profiles sum %d scenario runs; the timing interleaves "
             "%d scenario runs per variant." % (m["base_commit"], m["pin_sha256"][:16], m["golden_sha256"],
                                                m["reps"], m["timing_reps"]))
    L.append("")
    L.append("## The traces")
    L.append("")
    L.append("| variant | golden byte for byte | two runs identical | with the coarse probes | with the fine probes | first differing leaf |")
    L.append("|---|---|---|---|---|---|")
    for v, t in res["traces"].items():
        fd = t["first_diff"]
        L.append("| %s | %s | %s | %s | %s | %s |" % (
            v, t["golden"], t["deterministic"], t["coarse_probed_golden"], t["fine_probed_golden"],
            "—" if fd is None else "snapshot m%s `%s`, line %d: golden `%s`, variant `%s`" % (
                fd["minute"], fd["path"], fd["line"], fd["golden"], fd["variant"])))
    sk = res["slowK"]
    L.append("| slowK at K = 1 | %s | — | — | — | — |" % sk["k1_reproduces_golden"])
    L.append("")
    base = res["profiles"]["base"]["coarse"]
    rep = res["profiles"]["base"]["coarse_repeat"]
    bl = base["blocks"]
    L.append("## The baseline profile (E1, offline half)")
    L.append("")
    L.append("A probe pair costs %.3f µs (c_pair, calibrated in the same runtime; the block's own pair and every "
             "nested pair are subtracted). %d pipeline runs; the probe stack unwound %d times and found %d orphans. "
             "The repeat column is a second %d-scenario profile. C-Lua µs are for scale only." % (
                 base["c_pair_us"], base["pipeline_runs"], base["unwound"], base["orphan"], m["reps"]))
    L.append("")
    L.append("| step or block | share of the pipeline | repeat | share of its step | C-Lua µs per pipeline run | runs |")
    L.append("|---|---|---|---|---|---|")
    for s in STEPS:
        if s in bl:
            b = bl[s]
            L.append("| **%s** | %s %% | %s %% | — | %s | %d |" % (
                s, _f(100 * b["share_pipeline"]), _f(100 * rep["blocks"][s]["share_pipeline"]),
                _f(b["us_per_pipeline_run"]), b["count"]))
    for i, b in _top(bl):
        L.append("| %s | %s %% | %s %% | %s %% | %s | %d |" % (
            i, _f(100 * b["share_pipeline"]), _f(100 * rep["blocks"].get(i, {}).get("share_pipeline", float("nan"))),
            _f(100 * b.get("share_step", float("nan"))), _f(b["us_per_pipeline_run"], 2), b["count"]))
    heal = sum(bl[i]["share_pipeline"] for i in HEAL_IDS if i in bl)
    nheal = bl["nutrients/heal.pre"]["share_pipeline"] + bl["nutrients/heal.post"]["share_pipeline"]
    L.append("")
    L.append("- **The seven heal passes are %s %% of the pipeline** (repeat %s %%); the two Nutrients heals alone are "
             "%s %%. E1's rule (a heal total of 20 %% or more adopts E2) is met." % (
                 _f(100 * heal), _f(100 * sum(rep["blocks"][i]["share_pipeline"] for i in HEAL_IDS if i in rep["blocks"])),
                 _f(100 * nheal)))
    L.append("- The ten largest sub-blocks by share of the pipeline:")
    for n, (i, b) in enumerate(_top(bl, 10), 1):
        L.append("  %d. `%s` %s %% (%s %% of its step)" % (n, i, _f(100 * b["share_pipeline"]),
                                                            _f(100 * b.get("share_step", float("nan")))))
    L.append("")
    fine = res["profiles"]["base"]["fine"]["blocks"]
    rec = fine.get("nutrients/records")
    runs = res["profiles"]["base"]["fine"]["pipeline_runs"]
    L.append("### Inside the record engine (the fine pass)")
    L.append("")
    L.append("Kernel functions wrapped at run time (a vararg wrapper each, so the small functions are inflated: "
             "read the order, not the size). Shares are of `nutrients/records`; two's own kEff and requirement "
             "calls sit inside two's inclusive time.")
    L.append("")
    L.append("| function | calls per pipeline run | inclusive | exclusive |")
    L.append("|---|---|---|---|")
    kids = 0.0
    for i, b in sorted(fine.items(), key=lambda t: -t[1]["excl_s"]):
        if i.startswith("records/") and rec:
            kids += b["excl_s"]
            L.append("| %s | %s | %s %% | %s %% |" % (i[8:], _f(b["count"] / runs, 2), _f(100 * b["incl_s"] / rec["incl_s"]),
                                                    _f(100 * b["excl_s"] / rec["incl_s"])))
    if rec:
        L.append("| the loop and the wrappers' own calls | — | — | %s %% |" % _f(100 * (rec["incl_s"] - kids) / rec["incl_s"]))
    L.append("")
    tm = res["timing"]
    L.append("## Heal once (E2)")
    L.append("")
    L.append("Two placements of the one heal, each with the Nutrients key prefixes built lazily (only when a bad "
             "field is found); Strength's single heal is unchanged in both.")
    L.append("- **heal1** (the plan's wording, review risk 5's candidate): one heal after the step; the pre-step "
             "heals of Nutrients, Metabolism and Effects removed.")
    L.append("- **heal1pre**: one heal before the step; the post-step heals removed.")
    L.append("")
    L.append("| variant | golden | median C-Lua µs per pipeline run (sd) | saving, paired median | base share of the heals it removes |")
    L.append("|---|---|---|---|---|")
    pre = sum(bl[i]["share_pipeline"] for i in ("nutrients/heal.pre", "metabolism/heal.pre", "effects/heal.pre"))
    post = sum(bl[i]["share_pipeline"] for i in ("nutrients/heal.post", "metabolism/heal.post", "effects/heal.post"))
    for v, removed in (("base", ""), ("heal1", "%s %%" % _f(100 * pre)), ("heal1pre", "%s %%" % _f(100 * post))):
        t = tm[v]
        L.append("| %s | %s | %s (%s) | %s | %s |" % (v, res["traces"][v]["golden"], _f(t["median_us"]), _f(t["sd_us"]),
                                                      "—" if v == "base" else _ratio(t), removed))
    for v in ("heal1", "heal1pre"):
        pb = res["profiles"][v]["coarse"]["blocks"]
        kept = [i for i in HEAL_IDS if i in pb]
        L.append("")
        L.append("- %s's profile: the heals it keeps are %s %% of its pipeline (%s)." % (
            v, _f(100 * sum(pb[i]["share_pipeline"] for i in kept)),
            ", ".join("`%s` %s %%" % (i, _f(100 * pb[i]["share_pipeline"])) for i in kept)))
    L.append("")
    mu = res["mutation"]
    L.append("### The mutation pass")
    L.append("")
    L.append("Each run carries one NaN, injected into %s's record at minute %d (the golden's own minute-115 NaN is "
             "dropped from these runs; with no injection heal1 and heal1pre equal the base: %s). Two classes:" % (
                 INJECT_PLAYER, INJECT_MINUTE, mu["no_injection_equal_to_base"]))
    L.append("- **input**: written into the record between minutes, before the minute runs (a corrupted load, "
             "another writer, Intake's `ax`/`axr` and pending sums): the class the pre-step heals guard;")
    L.append("- **arithmetic**: left by the step itself, set NaN right after the kernel call that precedes the "
             "step's post heal: the class the post-step heals guard.")
    L.append("")
    L.append("Columns per variant: the state (every snapshot's records, players, sends and syncs; the adapters' "
             "counters and the log-line count left out) equals the base's under the same "
             "injection; the heal log line equals the base's; the non-finite numbers left in the record after the "
             "minute; whether the mutant that removes the variant's remaining heal in that adapter is killed (its "
             "trace, log or finiteness differs from the variant's).")
    L.append("")
    for cls in ("input", "arithmetic"):
        L.append("| class | adapter | injected | heal1 state = base | heal1 log = base | heal1 NaN left | heal1 mutant killed | heal1pre state = base | heal1pre log = base | heal1pre NaN left | heal1pre mutant killed |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for r in mu[cls]:
            cells = []
            for v in ("heal1", "heal1pre"):
                x = r["variants"][v]
                mk = x.get("mutant")
                cells += [str(x["state_equal_to_base"]), str(x["heal_lines_equal_to_base"]),
                          ", ".join(x["nonfinite_after_minute"][:4]) + (" …" if len(x["nonfinite_after_minute"]) > 4 else "") or "none",
                          "—" if mk is None else str(mk["killed"])]
            L.append("| %s | %s | `%s` | %s |" % (cls, r["adapter"], r["path"], " | ".join(cells)))
        L.append("")
    for cls in ("input", "arithmetic"):
        rows = mu[cls]
        for v in ("heal1", "heal1pre"):
            st = sum(1 for r in rows if r["variants"][v]["state_equal_to_base"])
            lg = sum(1 for r in rows if r["variants"][v]["heal_lines_equal_to_base"])
            nl = sum(1 for r in rows if r["variants"][v]["nonfinite_after_minute"])
            mk = [r["variants"][v]["mutant"]["killed"] for r in rows if r["variants"][v].get("mutant")]
            L.append("- %s, %s class: state equal to the base in %d of %d; log equal in %d; a NaN left after the "
                     "minute in %d; mutants killed %d of %d." % (v, cls, st, len(rows), lg, nl, sum(mk), len(mk)))
    L.append("")
    for cls in ("input", "arithmetic"):
        for r in mu[cls]:
            for v in ("heal1", "heal1pre"):
                x = r["variants"][v]
                if not x["state_equal_to_base"]:
                    fd = x["first_state_diff"]
                    L.append("- %s, %s `%s`: first differing leaf at snapshot m%s `%s` (base `%s`, %s `%s`)." % (
                        v, cls, r["path"], fd["minute"], fd["path"], fd["golden"], v, fd["variant"]))
    L.append("")
    L.append("## Hoisted constants (E3)")
    L.append("")
    hp = res["profiles"]["hoist"]["coarse"]["blocks"]
    L.append("| variant | golden | median C-Lua µs per pipeline run (sd) | saving, paired median | `nutrients/records` C-Lua µs per run (share of the pipeline) |")
    L.append("|---|---|---|---|---|")
    for v, pb in (("base", bl), ("hoist", hp)):
        t = tm[v]
        L.append("| %s | %s | %s (%s) | %s | %s (%s %%) |" % (
            v, res["traces"][v]["golden"], _f(t["median_us"]), _f(t["sd_us"]), "—" if v == "base" else _ratio(t),
            _f(pb["nutrients/records"]["us_per_pipeline_run"], 2), _f(100 * pb["nutrients/records"]["share_pipeline"])))
    L.append("")
    L.append("## A slow tier (E4)")
    L.append("")
    L.append("The 27 nutrient records (K.nutrients.minute, the excess ladder inside it) and the effects rebuild run "
             "every K game minutes in a per-player slot (hash(username) mod K), the absorbed and ingested amounts "
             "and dtM summed between slow steps; everything else keeps its minute. A diagnostic arm keeps the "
             "rebuild check every minute (the records alone on the slow tier). Both reproduce the golden at K = 1 "
             "(%s, %s)." % (sk["k1_reproduces_golden"], sk["k1_records_only_reproduces_golden"]))
    L.append("")
    L.append("Judged against the base run (k = 1) with P2's `compare` and P2's fairer band (memo Appendix H):")
    L.append("- a continuous leaf passes within 1 % of its field's range over every player's base snapshots "
             "(1e-3 absolute for a field under 0.1 in magnitude); a leaf constant over the base run passes on "
             "1e-3 absolute; first sight needs no alignment here (the fast tier keeps the minute);")
    L.append("- a leaf outside that band is **explained by the delay** when its slowK value is within the band of "
             "the base value at some minute at most K online minutes away;")
    L.append("- every band and grade leaf (%d paths: effects key bands, nutrient grades and excess rungs, the "
             "aggregates, traits, the perk) is followed minute by minute; a change matches when the value is the "
             "same and it lands at most K online minutes early or late; a base change within K minutes before "
             "g4's departure (minute 150) or the run's end is **clipped** (the slow tier could not show it in "
             "time); anything else is a **flip**." % sk["grade_paths_followed"])
    L.append("")
    for arm, title in (("k", "the plan's E4: records and the effects rebuild on the slow tier"),
                       ("k_records_only", "diagnostic: the records alone (the rebuild check every minute)")):
        L.append("### %s" % title[0].upper() + title[1:])
        L.append("")
        L.append("| K | two runs identical | outside the fairer band | of them explained by the delay | unexplained | band/grade leaves that changed | max delay (min) | clipped | flips | printed (base) | effects rebuilds (base) | no flip | no flip and no unexplained leaf |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for k in KS:
            r = _kv(sk[arm], k)
            L.append("| %d | %s | %d | %d | %d | %d | %d | %s | %s | %d (%d) | %d (%d) | %s | %s |" % (
                k, r["deterministic"], r["fair_outside"], r["fair_explained_by_delay"], r["fair_unexplained"],
                len(r["grade_changed"]), r["max_grade_delay"], ", ".join("`%s`" % p for p in r["clipped"]) or "none",
                ", ".join("`%s`" % p for p in r["flips"]) or "none", r["printed_count"], r["base_printed_count"],
                r["effects_rebuilds_m240"]["slowK"], r["effects_rebuilds_m240"]["base"], r["safe_grades"], r["safe_fair"]))
        L.append("")
        for k in KS:
            r = _kv(sk[arm], k)
            L.append("- **K = %d.**" % k)
            for p, a in r["grade_changed"].items():
                L.append("  - `%s`: %s; delays %s; clipped %s; base %s; slowK %s." % (
                    p, "FLIP at %s" % (a["flip"],) if a["flip"] else "matched", [x[2] for x in a["matched"]],
                    [(c["minute"], c["value"]) for c in a["clipped"]] or "none", a["base_events"][:10], a["slowK_events"][:10]))
            if r["fair_unexplained_fields"]:
                L.append("  - Unexplained continuous leaves by field: %s." % ", ".join(
                    "`%s` %d" % (f, n) for f, n in r["fair_unexplained_fields"].items()))
                for c in r["fair_unexplained_worst"][:5]:
                    L.append("    - m%d `%s`: base %s, slowK %s (abs %s, band %s)." % (
                        c["minute"], c["path"], CM._fmt(c["base"]), CM._fmt(c["other"]), CM._fmt(c["abs"]), CM._fmt(c["tol"])))
        L.append("")
    L.append("### The cost a slow tier moves off the minute")
    L.append("")
    sl = bl["nutrients/records"]["share_pipeline"] + bl["effects/rebuild"]["share_pipeline"]
    L.append("Base shares: `nutrients/records` %s %% and `effects/rebuild` %s %%, together %s %% of the pipeline. "
             "A slow tier at K moves (1 − 1/K) of that off the average player-minute; the slot minute still pays "
             "it whole, and the summing it adds (`nutrients/slowAcc`) is paid every minute." % (
                 _f(100 * bl["nutrients/records"]["share_pipeline"]), _f(100 * bl["effects/rebuild"]["share_pipeline"]),
                 _f(100 * sl)))
    L.append("")
    L.append("| K | arithmetic: share removed | measured: median C-Lua µs per run | measured: saving, paired median | slowK profile: `nutrients/records` + `effects/rebuild` | `nutrients/slowAcc` |")
    L.append("|---|---|---|---|---|---|")
    for k in KS:
        t = tm["slowK@K=%d" % k]
        pb = res["profiles"]["slowK@K=%d" % k]["coarse"]["blocks"]
        L.append("| %d | %s %% | %s | %s | %s %% | %s %% |" % (
            k, _f(100 * sl * (1 - 1.0 / k)), _f(t["median_us"]), _ratio(t),
            _f(100 * (pb["nutrients/records"]["share_pipeline"] + pb["effects/rebuild"]["share_pipeline"])),
            _f(100 * pb.get("nutrients/slowAcc", {}).get("share_pipeline", float("nan")))))
    L.append("")
    L.append("## What this does not settle")
    L.append("")
    L.append("- C Lua is not Kahlua: the shares rank the blocks; the live H2 timers give the milliseconds.")
    L.append("- The scenario is 240 game minutes: no nutrient grade moves in it, so the slow tier's grade delays "
             "are tested only on the effects bands; the records' onsets run in days.")
    L.append("- The slow tier's accumulator is a transient table (lost at a restart in this prototype); a shipped "
             "design would store it or flush it at departure.")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
