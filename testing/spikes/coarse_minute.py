r"""Plan 10b Task P2: the slow minute run every k game minutes against every one (an offline drift study).

The scenario is the golden trace's (testing/tests/kernel/golden_trace.py, `run`), on the same server_host.Host,
with one change: the slow minute (every EveryOneMinute listener, h.minute(), then the drain's OnTick frames,
h.tick(TICKS)) fires only on the minutes m with m % k == 0. Everything else keeps its own minute:
  - the world age still advances one game minute per loop step (START_AGE + m/60);
  - NR_T.m and the engine's own minute (wound timers, infection, catch-a-cold) still run every minute;
  - every event (meals, the drinks, g6's store raise, g3's death and OnNewGame, the NaN injection, g4's departure
    and return, the mirror request) lands at its own minute, between fired minutes when k does not divide it;
  - the snapshots are taken at the same minutes (every 30th; every k studied divides 30, so each snapshot follows
    a fired minute, and minute 240, the scenario's end, is fired for every k).

The first fired minute (`first` argument): by default the first fired minute is minute k, so a player's first
sight (and record, body and stomach) comes k - 1 minutes later than under k = 1, as a joining player's would. The
diagnostic `first=True` also fires minute 1, so every k starts from the same first sight and the drift left is
the cadence's own; the summary reports it beside the verdict, never as the verdict.

The ticks on the minutes that do not fire (`ticks` argument):
  - "fired" (the default, the outputs): no OnTick frame on an unfired minute. This is a coarse EveryOneMinute.
  - "every": 25 OnTick frames every minute, fired or not. This is a coarse minute with the per-tick drain still
    running; on an unfired minute the queue is empty and the drain takes its early-out.
  The two differ only through the drain's queue; the summary records whether their traces are byte-identical.

run_k(k) imports the golden module's host, players, events and serialisation and repeats only its loop, so
run_k(1) is golden_trace.run and serialises byte for byte to golden/trace-1.0.0.json (checked by --check-golden
and by every main run).

compare(base, other) flattens both traces' snapshots to leaves keyed "<minute>/<path>" and classifies each leaf:
  - continuous: a numeric leaf of a record or a stand-in player that is not discrete state (below). Its drift is
    |other - base| and, relative, that over the leaf's range across the base run's eight snapshots (the leaf's own
    path at every snapshot minute). Ruling 4's band: within 1 % of that range, or within 1e-3 absolute when the
    leaf's magnitude over the base run stays under 0.1.
  - discrete state: every string and boolean of a record or a stand-in player (bands, traits held, the dead flag,
    allReplete, nightVision, ...) and the named discrete numbers: effects.key.*, *Grade, the Strength perk level,
    and any numeric record or player leaf integral at every base snapshot that is also integral in the other run
    (a day index, a starved-day count; an integral base leaf that comes back non-integral is a continuous leaf
    that happened to sit on an integer, and is measured as continuous). Compared for equality.
  - telemetry counter: every leaf of stats, sent, syncs, instanced, printed_count, and the stand-in player's
    call and write counters (sets, traitApplies, writes, *Writes, regenSets, coldSets, reduceCalls). Compared for
    equality and reported in full; most count calls of the minute and scale with 1/k by construction, so they are
    reported as findings beside the verdict, not counted as state.
  - a leaf present in one trace and absent from the other: a structural mismatch (discrete state).
A k is safe under ruling 4 when it has no discrete-state mismatch and no continuous leaf outside the band.

    python testing/spikes/coarse_minute.py              runs k = 1, 2, 5, 10, 15, 30; writes out/coarse-k<k>.json
                                                        and out/coarse-summary.md
    python testing/spikes/coarse_minute.py --check-golden   k = 1 against the golden only
    python testing/spikes/coarse_minute.py --digest     prints each run's sha256 (the determinism check)
"""
import hashlib
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
KERNEL_TESTS = os.path.join(REPO, "testing", "tests", "kernel")
if KERNEL_TESTS not in sys.path:
    sys.path.insert(0, KERNEL_TESTS)

import golden_trace as G  # noqa: E402

OUT = os.path.join(HERE, "out")
KS = (1, 2, 5, 10, 15, 30)
BAND_REL = 0.01
BAND_ABS = 1e-3
SMALL = 0.1
WORST = 20

# The headline fields the summary tabulates for every k (a reading aid; the verdict reads every leaf).
HEADLINE = ("records:stomachFill", "records:body/fm", "records:body/lm", "players:nutrition/weight",
            "records:body/energyState", "records:body/inDay", "records:body/inDayClosed", "records:pool/calories",
            "players:nutrition/cal", "records:fluids/water", "records:fluids/thirstTarget", "records:fluids/dehydPct",
            "records:acute/bac", "records:acute/caf", "records:effects/panicTarget", "records:effects/tempTarget",
            "records:fluids/sweatLmin")
COUNTER_KEYS = {"sets", "traitApplies", "writes", "regenSets", "coldSets", "reduceCalls"}
TELEMETRY_ROOTS = ("stats", "sent", "syncs", "instanced", "printed_count")


# --- the scenario, the minute decimated -------------------------------------------------------------------

def run_k(k, ticks="fired", host=None, first=False):
    """golden_trace.run with the slow minute fired every k game minutes; the same snapshot shape."""
    if k < 1 or G.MINUTES % k != 0 or G.SNAPSHOT_EVERY % k != 0:
        raise ValueError("k must divide both the run (240) and the snapshot interval (30): %r" % k)
    if ticks not in ("fired", "every"):
        raise ValueError("ticks is 'fired' or 'every': %r" % ticks)
    h = host if host is not None else G.new_host()
    players = {n: G._new_player(h, n, G.MACROS[n]) for n in G.NAMES}
    order = list(G.NAMES)

    def publish():
        h.online(*[players[n] for n in order])

    publish()
    h.T.age = G.START_AGE
    snapshots = []
    pre_sight = []
    for m in range(1, G.MINUTES + 1):
        h.T.age = G.START_AGE + m / 60.0
        h.T.m = m
        h.T.engine()
        if m in G.MEAL_MINUTES:
            for n in order:
                rec = h.record(n)
                if rec is None or rec["stomach"] is None:
                    # a meal before the player's first fired minute (k >= 10: the minute-10 round): the golden's
                    # guard is a scenario check, so the mod's own path runs (IN.readAfterAndLand creates the
                    # record through store.get and seeds the stomach full), and the meal is counted
                    pre_sight.append("m%d:%s" % (m, n))
                    h.T.eat(m, n)
                else:
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
        if m == 115:
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
        fired = (m % k == 0) or m == G.MINUTES or (first and m == 1)
        if fired:
            h.minute()
        if fired or ticks == "every":
            h.tick(G.TICKS)
        if m % G.SNAPSHOT_EVERY == 0:
            snapshots.append(G._snapshot(h, m, players))
    run_k.pre_sight = pre_sight            # beside the trace, so run_k(1)'s shape stays golden_trace.run's
    return {"snapshots": snapshots, "printed_count": len(h.printed())}


run_k.pre_sight = []


# --- the comparison ----------------------------------------------------------------------------------------

def _flatten(v, path, out):
    if isinstance(v, dict):
        for key in sorted(v):
            _flatten(v[key], path + "/" + key if path else key, out)
    else:
        out[path] = v


def _leaves(trace_json):
    """{(minute, path): value} over the snapshots, plus printed_count at minute 0."""
    out = {}
    for snap in trace_json["snapshots"]:
        flat = {}
        _flatten({k: v for k, v in snap.items() if k != "minute"}, "", flat)
        for p, v in flat.items():
            out[(snap["minute"], p)] = v
    out[(0, "printed_count")] = trace_json["printed_count"]
    return out


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _integral(v):
    return _is_num(v) and math.isfinite(v) and float(v) == math.floor(v)


def _is_telemetry(path):
    root = path.split("/", 1)[0]
    if root in TELEMETRY_ROOTS:
        return True
    last = path.rsplit("/", 1)[-1]
    if root == "players" and (last in COUNTER_KEYS or last.endswith("Writes")):
        return True
    return False


_NAMED_DISCRETE = (re.compile(r"/effects/key/"), re.compile(r"Grade$"), re.compile(r"^players/[^/]+/st/perk$"))


def _named_discrete(path):
    return any(r.search(path) for r in _NAMED_DISCRETE)


def compare(base, other):
    """Per-leaf drift of `other` against `base` (both run_k dicts or their parsed JSON), and every mismatch."""
    b = _leaves(json.loads(G.serialize(base)))      # either form normalises through the golden serialisation
    o = _leaves(json.loads(G.serialize(other)))
    # per-path range and magnitude over the base run (the eight snapshots)
    by_path = {}
    for (m, p), v in b.items():
        by_path.setdefault(p, []).append(v)
    rng, mag, integral = {}, {}, {}
    by_field = {}
    for p, vals in by_path.items():
        nums = [float(x) for x in vals if _is_num(x) and math.isfinite(x)]
        if nums:
            rng[p] = max(nums) - min(nums)
            mag[p] = max(abs(x) for x in nums)
            by_field.setdefault(_field(p), []).extend(nums)
        integral[p] = all(_integral(x) for x in vals)
    # the secondary reading (never the verdict): the field's range over every player's snapshots
    frng = {f: max(v) - min(v) for f, v in by_field.items()}
    fmag = {f: max(abs(x) for x in v) for f, v in by_field.items()}
    continuous, discrete, telemetry, structural = [], [], [], []
    for key in sorted(set(b) | set(o), key=lambda t: (t[0], t[1])):
        m, p = key
        if key not in b or key not in o:
            structural.append({"minute": m, "path": p, "base": b.get(key, "<absent>"), "other": o.get(key, "<absent>")})
            continue
        vb, vo = b[key], o[key]
        if _is_telemetry(p):
            if vb != vo:
                telemetry.append({"minute": m, "path": p, "base": vb, "other": vo})
            continue
        both_num = _is_num(vb) and _is_num(vo)
        if not both_num or _named_discrete(p) or (integral.get(p) and _integral(vo)):
            if vb != vo:
                discrete.append({"minute": m, "path": p, "base": vb, "other": vo})
            continue
        if not (math.isfinite(vb) and math.isfinite(vo)):
            if not (vb == vo or (math.isnan(vb) and math.isnan(vo))):
                discrete.append({"minute": m, "path": p, "base": vb, "other": vo, "note": "non-finite"})
            continue
        d = abs(vo - vb)
        r = rng.get(p, 0.0)
        small = mag.get(p, 0.0) < SMALL
        rel = (d / r) if r > 0 else (0.0 if d == 0 else math.inf)
        ok = (d <= BAND_ABS) if small else (d <= BAND_REL * r)
        f = _field(p)
        fr = frng.get(f, 0.0)
        ok_field = (d <= BAND_ABS) if fmag.get(f, 0.0) < SMALL else (d <= BAND_REL * fr)
        continuous.append({"minute": m, "path": p, "base": vb, "other": vo, "abs": d, "range": r, "rel": rel,
                           "small": small, "in_band": ok, "in_field_band": ok_field})
    nonzero = [c for c in continuous if c["abs"] > 0]
    worst = sorted(nonzero, key=lambda c: (-c["rel"], -c["abs"], c["minute"], c["path"]))[:WORST]
    failing = [c for c in continuous if not c["in_band"]]
    max_rel = max([c["rel"] for c in continuous] or [0.0])
    return {
        "leaves": len(continuous) + len(discrete) + len(telemetry) + len(structural),
        "continuous_leaves": len(continuous),
        "continuous_moved": len(nonzero),
        "max_rel": max_rel,
        "max_abs": max([c["abs"] for c in continuous] or [0.0]),
        "worst": worst,
        "failing": failing,
        "headline": {f: {"max_abs": max([c["abs"] for c in continuous if _field(c["path"]) == f] or [0.0]),
                         "field_range": frng.get(f, 0.0),
                         "out": sum(1 for c in failing if _field(c["path"]) == f),
                         "n": sum(1 for c in continuous if _field(c["path"]) == f)} for f in HEADLINE},
        "failing_field": [c for c in continuous if not c["in_field_band"]],
        "failing_tiny": [c for c in failing if c["abs"] <= BAND_ABS],
        "failing_m240": [c for c in failing if c["minute"] == 240],
        "discrete": discrete,
        "structural": structural,
        "telemetry": telemetry,
        "safe": not discrete and not structural and not failing,
    }


# --- the outputs --------------------------------------------------------------------------------------------

def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _golden_text():
    with open(G.GOLDEN, encoding="utf-8", newline="") as fh:
        return fh.read()


def _fmt(v):
    if _is_num(v):
        return "%.6g" % v
    return json.dumps(v)


def _field(path):
    """A path with its snapshot-independent part, for grouping: records/g1/body/fm -> body/fm."""
    parts = path.split("/")
    if parts[0] in ("records", "players") and len(parts) > 2:
        return parts[0] + ":" + "/".join(parts[2:])
    return path


def summary_md(results, texts, alt, pre, aligned):
    lines = []
    lines.append("# P2: the slow minute run every k game minutes against every one")
    lines.append("")
    lines.append("Generated by `testing/spikes/coarse_minute.py` (Plan 10b Task P2) over the golden trace's scenario "
                 "(`testing/tests/kernel/golden_trace.py`: six players, 240 game minutes, snapshots every 30th) "
                 "on `server_host.Host`, the mod tree at HEAD. The slow minute (`h.minute()` then "
                 "`h.tick(25)`) fires on minutes m with m % k == 0 (and minute 240, the end); the world age, the engine step, every event "
                 "and every snapshot keep their own minute. Off-minute ticks: none (`ticks=\"fired\"`).")
    lines.append("")
    lines.append("## Sanity")
    lines.append("")
    gold = _golden_text()
    lines.append("- golden `trace-1.0.0.json` sha256: `%s`" % _sha(gold))
    lines.append("- k = 1 sha256: `%s`; byte-identical to the golden: %s" % (_sha(texts[1]), texts[1] == gold))
    for k in KS:
        lines.append("- k = %d, ticks every minute (`ticks=\"every\"`) byte-identical to no off-minute ticks: %s"
                     % (k, alt[k]))
    for k in KS:
        lines.append("- k = %d, meals before the player's first fired minute (the mod's own path, the golden's "
                     "guard bypassed): %s" % (k, ", ".join(pre[k]) if pre[k] else "none"))
    lines.append("")
    lines.append("## Ruling 4's verdict per k")
    lines.append("")
    lines.append("Band: a continuous leaf within 1 % of its range over the k = 1 run, or within 1e-3 absolute "
                 "when its magnitude over that run stays under 0.1. Discrete state: strings, booleans, "
                 "effects.key, grades, the perk level, integral record leaves. Telemetry counters (stats, "
                 "sent, syncs, instanced, printed_count, the stand-in's write counters) are listed below, "
                 "not counted as state.")
    lines.append("")
    lines.append("| k | continuous leaves | moved | max relative drift | max absolute drift | outside the band "
                 "| discrete-state mismatches | structural | telemetry mismatches | safe |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for k in KS:
        r = results[k]
        lines.append("| %d | %d | %d | %s | %s | %d | %d | %d | %d | %s |" % (
            k, r["continuous_leaves"], r["continuous_moved"], _fmt(r["max_rel"]), _fmt(r["max_abs"]),
            len(r["failing"]), len(r["discrete"]), len(r["structural"]), len(r["telemetry"]),
            "yes" if r["safe"] else "no"))
    lines.append("")
    lines.append("Secondary readings (not the verdict): leaves outside the band whose absolute drift is itself "
                 "1e-3 or less (a near-constant leaf, its range over k = 1 tiny); leaves outside the band at the "
                 "last snapshot (minute 240) only; leaves outside the band when the range is the field's over "
                 "every player's snapshots instead of the leaf's own.")
    lines.append("")
    lines.append("| k | outside the band | of them, absolute drift <= 1e-3 | at minute 240 | outside a field-wide band |")
    lines.append("|---|---|---|---|---|")
    for k in KS:
        r = results[k]
        lines.append("| %d | %d | %d | %d | %d |" % (k, len(r["failing"]), len(r["failing_tiny"]),
                                                   len(r["failing_m240"]), len(r["failing_field"])))
    lines.append("")
    lines.append("## Headline fields")
    lines.append("")
    lines.append("Per field, over every player and snapshot: the largest absolute drift against k = 1, and in "
                 "brackets the leaves outside ruling 4's band of the leaves compared. The field range is the "
                 "field's over every player's k = 1 snapshots (a scale for the reader; the band uses each leaf's "
                 "own range).")
    lines.append("")
    lines.append("| field | range over k = 1 | " + " | ".join("k = %d" % k for k in KS if k != 1) + " |")
    lines.append("|---|---|" + "---|" * (len(KS) - 1))
    for f in HEADLINE:
        row = "| `%s` | %s |" % (f, _fmt(results[2]["headline"][f]["field_range"]))
        for k in KS:
            if k == 1:
                continue
            hd = results[k]["headline"][f]
            row += " %s (%d/%d) |" % (_fmt(hd["max_abs"]), hd["out"], hd["n"])
        lines.append(row)
    lines.append("")
    lines.append("## Diagnostic: minute 1 also fired (`first=True`), so every k shares k = 1's first sight")
    lines.append("")
    lines.append("Not the verdict: the same comparison against k = 1 with the first-sight lag removed, so what is "
                 "left is the cadence's own drift (integration over k minutes, a day closed up to k - 1 minutes "
                 "late, an event read up to k - 1 minutes late).")
    lines.append("")
    lines.append("| k | moved | max relative drift | max absolute drift | outside the band | of them, absolute "
                 "<= 1e-3 | discrete-state mismatches | structural | safe |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for k in KS:
        r = aligned[k]
        lines.append("| %d | %d | %s | %s | %d | %d | %d | %d | %s |" % (
            k, r["continuous_moved"], _fmt(r["max_rel"]), _fmt(r["max_abs"]), len(r["failing"]),
            len(r["failing_tiny"]), len(r["discrete"]), len(r["structural"]), "yes" if r["safe"] else "no"))
    lines.append("")
    lines.append("The headline fields, first-sight aligned (largest absolute drift; leaves outside the band / "
                 "compared):")
    lines.append("")
    lines.append("| field | " + " | ".join("k = %d" % k for k in KS if k != 1) + " |")
    lines.append("|---|" + "---|" * (len(KS) - 1))
    for f in HEADLINE:
        row = "| `%s` |" % f
        for k in KS:
            if k == 1:
                continue
            hd = aligned[k]["headline"][f]
            row += " %s (%d/%d) |" % (_fmt(hd["max_abs"]), hd["out"], hd["n"])
        lines.append(row)
    lines.append("")
    for k in KS:
        if k == 1:
            continue
        r = aligned[k]
        fields = {}
        for c in r["failing"]:
            fields.setdefault(_field(c["path"]), []).append(c)
        top = sorted(fields, key=lambda x: (-max(c["rel"] for c in fields[x]), x))[:10]
        lines.append("- k = %d, first-sight aligned: %d fields outside the band; the ten worst: %s; discrete: %s" % (
            k, len(fields), ", ".join("`%s` (%s)" % (f, _fmt(max(c["rel"] for c in fields[f]))) for f in top) or "none",
            ", ".join("m%d `%s` %s -> %s" % (d["minute"], d["path"], _fmt(d["base"]), _fmt(d["other"]))
                      for d in r["discrete"]) or "none"))
    lines.append("")
    for k in KS:
        if k == 1:
            continue
        r = results[k]
        lines.append("## k = %d" % k)
        lines.append("")
        fields = {}
        for c in r["failing"]:
            f = _field(c["path"])
            fields.setdefault(f, []).append(c)
        lines.append("### Fields outside the band (%d leaves, %d fields)" % (len(r["failing"]), len(fields)))
        lines.append("")
        if fields:
            lines.append("| field | leaves | worst relative | worst absolute | worst at |")
            lines.append("|---|---|---|---|---|")
            for f in sorted(fields, key=lambda x: (-max(c["rel"] for c in fields[x]), x)):
                cs = fields[f]
                w = max(cs, key=lambda c: (c["rel"], c["abs"]))
                lines.append("| `%s` | %d | %s | %s | m%d `%s` (%s -> %s, range %s) |" % (
                    f, len(cs), _fmt(w["rel"]), _fmt(w["abs"]), w["minute"], w["path"], _fmt(w["base"]),
                    _fmt(w["other"]), _fmt(w["range"])))
        else:
            lines.append("None.")
        lines.append("")
        lines.append("### Discrete-state mismatches (%d)" % len(r["discrete"]))
        lines.append("")
        if r["discrete"]:
            lines.append("| minute | path | k = 1 | k = %d |" % k)
            lines.append("|---|---|---|---|")
            for d in r["discrete"]:
                lines.append("| %d | `%s` | %s | %s |" % (d["minute"], d["path"], _fmt(d["base"]), _fmt(d["other"])))
        else:
            lines.append("None.")
        lines.append("")
        if r["structural"]:
            lines.append("### Structural mismatches (%d leaves), by minute and subtree" % len(r["structural"]))
            lines.append("")
            groups = {}
            for d in r["structural"]:
                parts = d["path"].split("/")
                sub = "/".join(parts[:3]) if len(parts) > 3 else d["path"]
                side = "absent at k = %d" % k if d["other"] == "<absent>" else "absent at k = 1"
                groups.setdefault((d["minute"], sub, side), 0)
                groups[(d["minute"], sub, side)] += 1
            lines.append("| minute | subtree | leaves | which side lacks it |")
            lines.append("|---|---|---|---|")
            for (mm, sub, side), n in sorted(groups.items()):
                lines.append("| %d | `%s` | %d | %s |" % (mm, sub, n, side))
            lines.append("")
        lines.append("### The worst %d continuous leaves by relative drift" % WORST)
        lines.append("")
        lines.append("| minute | path | k = 1 | k = %d | absolute | range over k = 1 | relative | in band |" % k)
        lines.append("|---|---|---|---|---|---|---|---|")
        for c in r["worst"]:
            lines.append("| %d | `%s` | %s | %s | %s | %s | %s | %s |" % (
                c["minute"], c["path"], _fmt(c["base"]), _fmt(c["other"]), _fmt(c["abs"]), _fmt(c["range"]),
                _fmt(c["rel"]), "yes" if c["in_band"] else "no"))
        lines.append("")
        lines.append("### Telemetry counters at minute 240 (%d mismatches over all snapshots)" % len(r["telemetry"]))
        lines.append("")
        last = [t for t in r["telemetry"] if t["minute"] in (240, 0)]
        if last:
            lines.append("| path | k = 1 | k = %d |" % k)
            lines.append("|---|---|---|")
            for t in last:
                lines.append("| `%s` | %s | %s |" % (t["path"], _fmt(t["base"]), _fmt(t["other"])))
        else:
            lines.append("None.")
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv):
    if "--check-golden" in argv:
        text = G.serialize(run_k(1))
        same = text == _golden_text()
        print("k=1 sha256 %s golden-identical %s" % (_sha(text), same))
        return 0 if same else 1
    texts, traces, pre = {}, {}, {}
    for k in KS:
        tr = run_k(k)
        traces[k] = tr
        texts[k] = G.serialize(tr)
        pre[k] = list(run_k.pre_sight)
    if "--digest" in argv:
        for k in KS:
            print("k=%d sha256 %s" % (k, _sha(texts[k])))
        return 0
    if texts[1] != _golden_text():
        print("k = 1 does not reproduce the golden trace: the harness is wrong", file=sys.stderr)
        return 1
    alt = {k: G.serialize(run_k(k, ticks="every")) == texts[k] for k in KS}
    parsed = {k: json.loads(texts[k]) for k in KS}
    results = {k: compare(parsed[1], parsed[k]) for k in KS}
    aligned = {k: compare(parsed[1], json.loads(G.serialize(run_k(k, first=True)))) for k in KS}
    os.makedirs(OUT, exist_ok=True)
    for k in KS:
        with open(os.path.join(OUT, "coarse-k%d.json" % k), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(texts[k])
    with open(os.path.join(OUT, "coarse-summary.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(summary_md(results, texts, alt, pre, aligned))
    for k in KS:
        r = results[k]
        print("k=%d max_rel=%s failing=%d discrete=%d structural=%d telemetry=%d safe=%s sha256=%s" % (
            k, _fmt(r["max_rel"]), len(r["failing"]), len(r["discrete"]), len(r["structural"]),
            len(r["telemetry"]), r["safe"], _sha(texts[k])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
