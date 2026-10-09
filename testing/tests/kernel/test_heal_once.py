"""Heal once, before the step (Plan 11 Task 12, ruling 10; Appendix J's heal1pre).

Metabolism, Nutrients and Effects heal their record sub-tables once, before the step's arithmetic. The post-step
heals are gone; in their place a post-step guard re-stamps, from its pre-step value, every field the step's own
arithmetic left non-finite that something reads before the next minute's pre-step heal. CROSS is Step 1's
enumeration of those reads: (producer step, record sub-table, field, consumer). The consumers are the steps after
the producer in NR.server.minute.ORDER (nutrients, effects, strength, weight, writer, store), and the readers that
run before the next minute's pre-step heals: the bus step, which runs FIRST in ORDER and so reads a step-made NaN
of the last minute before any heal ("bus": the push signature and K.mirror.build); Nutrients reads record.effects
at the next minute before Effects' pre-step heal. The writer (Plan 11 Task 14) replaced the takeover's per-tick
handler ("fast"); its rows are exactly the guarded fields it reads (test_the_writers_cross_rows_are_its_reads).
"kept" marks the two sleep-onset scalars no step reads since the takeover left: Effects still guards them (the
Task 14 amendment keeps EFF.GUARD intact), and the writer applies no onset term (its limitation string).
A ring slot is a sub-table path ("body.eb7", field 7): a day close shifts slots 1-6 from pre-step-healed values,
so only slot 7 (and bandWeek's slot 7) can take a value this minute's arithmetic made.

The store step reads every K.store.INPUTS path; its rows below are the guarded inputs. An unguarded input the
step leaves non-finite is saved as a missing key (the codec writes NaN as null) and loads as its constructor's
default (K.store.load), the fresh value the heal would have stamped; body's load needs fm, lm, sex and lastAgeH
(K.store.bodyBase), so fm, lm and lastAgeH are guarded (no step writes sex).

WINDOW lists the reads left unguarded, each with the reason; the window test injects each one and shows the NaN
stays in its own field for one minute and the next pre-step heal takes it (the accepted window, ruling 10).

Kinetics (Plan 11c Task 8) heals by resetting the stomach empty rather than re-stamping: its GUARD lists name the
fields that reset fires on (the liquid lane, the solid lane's energy, which sets every key's drain next minute, and
the gram keys of the mass); the writer's own pool P is guarded inside the writer (test_writer_shape.py). Two writes
and reads sit outside the minute: the intake feeds satiety.P at the eat (IN.feed), and the writer heals a
non-finite P by re-seeding it; the client's Overfull level reads the mirror's stomachMass, which K.mirror.stomachMass
reads as 0 for a non-finite mass, and K.view.fullnessLevel reads a non-finite mass as 0 as well. Metabolism's
satiety.L and body.exKcalPrev (Plan 11c Task 6) are re-stamped by its guard, and its pre-step heal
(MET.healActivity) stamps 0 on either when an input arrives non-finite.

The injections run on the shared host; each wraps a kernel function its producer step calls near its end, so the
NaN appears inside the producer's step as its own arithmetic would make it.
"""
import math

import pytest

from .server_host import Host


def _rows(producer, sub, consumers):
    return [(producer, sub, f, c) for c, fields in consumers for f in fields]


# K.vector.KEYS, in order: the stomach buffer's every key is guarded (ruling T8-1; an infinite gram key pins the fill,
# which the writer reads, at 1 and never drains; a non-finite micronutrient would spread into the pool and the nutrients).
BUFFER_KEYS = ("calories", "carbs", "lipids", "proteins", "fibre", "water", "vitC", "iron", "phytate",
               "retinol", "carotene", "vitD", "vitE", "vitK", "thiamine", "riboflavin", "niacin", "vitB6",
               "folate", "vitB12", "choline", "sodium", "potassium", "calcium", "magnesium", "zinc",
               "iodine", "selenium", "efa", "caffeine", "ethanol")

# Step 1's table: (producer, sub-table, field, consumer).
CROSS = (
    _rows("metabolism", "body", [
        ("nutrients", ("dayIndex", "inDayClosed", "fm", "lm", "lastCloseAgeH", "eeDay", "pPrevKg", "alcDay", "met",
                       "coldMult", "carbDay", "band1Day", "band2Day")),
        ("effects", ("fm", "lm", "dayIndex", "exKcalDay", "band1Day", "band2Day", "met", "inDayClosed")),
        ("strength", ("fm", "lm", "dayIndex", "n", "nPeak", "tPeakD", "cumDef", "tDisuse")),
        ("weight", ("fm", "lm", "pDay", "carbDay", "lipDay", "ebDay", "lastCloseAgeH")),
        ("kinetics", ("energyState",)),
        ("writer", ("energyState", "rmod", "met")),   # met: the heavy-work band of the acute term (Plan 11c Task 6)
        ("bus", ("energyState", "dmod", "rmod", "ebDay", "eeDay", "fm", "inDay", "lm", "tac", "vStr", "vHyp")),
        ("store", ("fm", "lm", "lastAgeH", "dayIndex", "lastCloseAgeH", "inDay", "eeDay", "ebDay", "exKcalDay",
                   "pDay", "carbDay", "lipDay", "alcDay", "inDayClosed", "pPrevKg", "band1Day", "band2Day", "n",
                   "nPeak", "tPeakD", "cumDef", "tDisuse", "tac", "vStr", "vHyp", "exKcalPrev")),
    ])
    + _rows("metabolism", "body.eb7", [("nutrients", (7,)), ("weight", (7,)), ("store", (7,))])
    + _rows("metabolism", "body.carb7", [("nutrients", (7,)), ("weight", (7,)), ("store", (7,))])
    + _rows("metabolism", "body.p7", [("effects", (7,)), ("weight", (7,)), ("store", (7,))])
    + _rows("metabolism", "body.lip7", [("weight", (7,)), ("store", (7,))])
    + _rows("metabolism", "body.mass7", [("store", (7,))])
    + _rows("metabolism", "body.bandWeek.7", [("nutrients", (1, 2)), ("store", (1, 2))])
    + _rows("nutrients", "fluids", [
        ("effects", ("dehydPct", "naPlasma")),
        ("strength", ("dehydPct",)),
        ("writer", ("thirstTarget",)),
        ("bus", ("dehydPct", "naPlasma", "thirstTarget")),
    ])
    + _rows("nutrients", "acute", [
        ("effects", ("caf", "wd", "cafTol", "bac", "alcPeak", "hang", "bg", "iuSleep", "debtH", "iu", "exEma",
                     "bmi", "starvedDays", "coldH", "lastVigAgeH", "retEma")),
        ("strength", ("awakeH", "caf")),
        ("writer", ("S", "circ", "debtH")),   # debtH: the sleep factor (Plan 11d Task 6, W.satietyFactor)
        ("bus", ("awakeH", "bac", "bg", "caf", "debtH", "g", "iu", "refeedRisk")),
        ("store", ("caf", "cafTol", "alcPeak", "hang", "bg", "awakeH", "debtH", "S", "starvedDays", "bmi", "exEma",
                   "lastVigAgeH", "coldH", "retEma", "refeedRisk")),
    ])
    + _rows("nutrients", "nutrients", [("effects", ("epoch",)), ("store", ("epoch",))])
    + _rows("effects", "effects", [
        ("writer", ("fOff", "stressTarget", "panicTarget", "unhappyTarget", "foodSickTarget", "tempTarget", "tempAdj",
                    "intoxTarget")),
        ("kept", ("solAddH", "solMul")),
        ("nutrients", ("mAcc", "rRec")),
        ("bus", ("epoch", "aimMul", "speedMul", "intoxTarget", "tempTarget", "healMul", "bleedMul", "infectMul",
                 "coldMul", "drain", "lethal", "stressTarget", "panicTarget", "unhappyTarget", "foodSickTarget",
                 "fOff", "mAcc", "rRec")),
        ("store", ("epoch",)),
    ])
    # Plan 11c Task 8: the exercise lag Metabolism steps, which the writer reads (to heal it) and the store saves.
    + _rows("metabolism", "satiety", [("writer", ("L",)), ("store", ("L",))])
    # Plan 11c Task 8: the stomach's two lanes. The pending water reads both lanes' water (K.stomach.water); the bus's
    # push signature and K.mirror.stomach read the whole mass, both lanes (K.stomach.mass via K.mirror.stomachMass).
    # Plan 11d Task 5 fix (ruling T5-2): the writer reads both lanes for its satiety F (W.satietyF, K.stomach.fullnessMass).
    + _rows("kinetics", "stomach", [("nutrients", ("liquid",)), ("bus", ("liquid",)), ("writer", ("liquid",)),
                                    ("store", ("liquid",))])
    + _rows("kinetics", "stomach.buffer", [
        ("nutrients", ("water",)),
        ("bus", ("water", "proteins", "carbs", "lipids", "fibre")),
        ("writer", BUFFER_KEYS),          # every key: W.bufferFinite (Plan 11d close, ruling C-1)
        ("store", BUFFER_KEYS),
    ])
)
# The ctx transients Metabolism stamps for the writer (ctx.activityClass, ctx.exercising) live one player's minute
# on the pipeline context, never on the record, so they have no rows.

# The kernel function each producer calls near its step's end: the injection lands after it returns.
NEAR_END = {"metabolism": "energy.state", "nutrients": "acute.iu", "effects": "effects.drain", "kinetics": "stomach.fill"}

# Every guarded (producer, sub-table, field), once.
GUARDED = sorted({(p, s, f) for p, s, f, _ in CROSS}, key=lambda r: (r[0], r[1], str(r[2])))
INJECT = [(p, NEAR_END[p], s, f) for p, s, f in GUARDED]

# The reads left unguarded: (producer, sub-table, field, reason). Each is injected by the window test.
WINDOW = [
    ("nutrients", "fluids", "viewPct", "read only inside the Nutrients step, before thirstTarget"),
    ("nutrients", "fluids", "c", "read only inside the Nutrients step, before naPlasma and thirstTarget"),
    ("nutrients", "acute", "glyc", "a store input only: a missing key loads the constructor's value"),
    ("nutrients", "fluids", "water", "a store input only"),
    ("nutrients", "acute", "cafMean", "a store input only"),
    ("nutrients", "nutrients.vitC", "g", "Effects reads it through comparisons only (a rung literal by construction)"),
    ("nutrients", "nutrients.iron", "x", "Effects reads it through comparisons only (a rung literal by construction)"),
    ("nutrients", "nutrients.thiamine", "ah", "Effects' drain compares it only (a finite sum by construction)"),
    ("nutrients", "nutrients.vitC", "e24", "Effects' cold credit compares it only (finite inputs by the intake guard)"),
    ("nutrients", "nutrients.vitA", "g", "the mirror reads nutrients.<key>.g/.p/.x for every ORDER key (K.mirror.nutrients): "
     "one mirror carries the NaN and the client blanks it (K.view.fmt renders NaN as \"\"); guarding them would cost "
     "about three keys times the ORDER length per minute"),
    ("nutrients", "nutrients.vitA", "p", "as .g: one mirror carries the NaN, the client blanks it"),
    ("nutrients", "nutrients.vitA", "x", "as .g: one mirror carries the NaN, the client blanks it"),
    ("nutrients", "body", "alcDay", "written by Nutrients after Metabolism's guard; only the store reads it, and a null "
     "on save loads 0, the heal's neutral"),
    ("effects", "effects", "nvDays", "a store input only; Effects reads it next minute after its heal"),
]

WRAP = r"""
function(path, rec, sub, field)
    local K = NutritionRevamp.kernel
    local seg1, seg2 = string.match(path, "^(%w+)%.(%w+)$")
    local orig = K[seg1][seg2]
    K[seg1][seg2] = function(...)
        local r1, r2, r3 = orig(...)
        local t = rec
        for seg in string.gmatch(sub, "[^%.]+") do
            local n = tonumber(seg)
            if n ~= nil then t = t[n] else t = t[seg] end
        end
        t[field] = 0/0
        K[seg1][seg2] = orig
        return r1, r2, r3
    end
end
"""


def nonfinite(t, prefix=""):
    out = []
    for k, v in t.items():
        if isinstance(v, float) and not math.isfinite(v):
            out.append(prefix + str(k))
        elif hasattr(v, "items"):
            out.extend(nonfinite(v, prefix + str(k) + "."))
    return out


def settle():
    h = Host()
    p = h.player("a")
    h.online(p)
    for m in range(1, 4):
        h.T.age = 100.0 + m / 60
        h.minute(); h.tick(25)
    return h


def next_minute(h, m):
    h.T.age = 100.0 + m / 60
    h.minute(); h.tick(25)


def test_cross_and_window_are_disjoint():
    guarded = {(p, s, f) for p, s, f in GUARDED}
    assert not guarded & {(p, s, f) for p, s, f, _ in WINDOW}


def test_the_guard_lists_are_step_1s_table():
    h = Host()
    N = h.NR.server
    lua = lambda t: sorted(str(v) for v in t.values())
    want = lambda prod, sub: sorted(str(f) for p, s, f in GUARDED if p == prod and s == sub)
    assert lua(N.metabolism.GUARD) == want("metabolism", "body")
    assert lua(N.metabolism.GUARD_RINGS) == sorted(s.split(".")[1] for p, s, f in GUARDED
                                                   if p == "metabolism" and s.count(".") == 1)
    assert lua(N.metabolism.BAND_SLOT) == want("metabolism", "body.bandWeek.7")
    assert lua(N.nutrients.GUARD_FLUIDS) == want("nutrients", "fluids")
    assert lua(N.nutrients.GUARD_ACUTE) == want("nutrients", "acute")
    assert lua(N.nutrients.GUARD_STATE) == want("nutrients", "nutrients")
    assert lua(N.effects.GUARD) == want("effects", "effects")
    assert lua(N.metabolism.GUARD_SATIETY) == want("metabolism", "satiety")
    assert lua(N.kinetics.GUARD) == want("kinetics", "stomach")
    assert want("kinetics", "stomach.buffer") == lua(h.NR.kernel.vector.KEYS)
    assert want("kinetics", "stomach.buffer") == sorted(BUFFER_KEYS)


@pytest.mark.parametrize("producer,fn,sub,field", INJECT)
def test_a_step_made_nan_never_spreads_in_its_minute(producer, fn, sub, field):
    h = settle()
    rec = h.record("a")
    t = rec
    for seg in sub.split("."):
        t = t[int(seg)] if seg.isdigit() else t[seg]
    if t[field] is None:
        t[field] = 1500.0                               # inDayClosed: a body past its first close holds a stamp
    h.rt.eval(WRAP)(fn, rec, sub, field)
    next_minute(h, 4)
    bad = nonfinite(rec)
    assert bad == [], (producer, sub, field, bad)      # guarded: re-stamped before any later step read it


@pytest.mark.parametrize("producer,sub,field,reason", WINDOW)
def test_an_unguarded_field_keeps_its_nan_one_minute_alone_then_heals(producer, sub, field, reason):
    h = settle()
    rec = h.record("a")
    h.rt.eval(WRAP)(NEAR_END[producer], rec, sub, field)
    next_minute(h, 4)
    assert nonfinite(rec) == [sub + "." + str(field)], reason    # contained: no other field took it up
    next_minute(h, 5)
    assert nonfinite(rec) == []                                  # the next pre-step heal took it


def test_a_guard_that_restamps_counts_and_logs():
    h = settle()
    rec = h.record("a")
    before = rec.body.fm
    h.rt.eval(WRAP)("energy.state", rec, "body", "fm")
    n0 = len(h.printed())
    next_minute(h, 4)
    assert h.NR.server.metabolism.guarded == 1
    assert rec.body.fm == before                                  # this minute's change to fm is lost with the NaN
    said = [s for s in h.printed()[n0:] if "re-stamped" in s]
    assert said == ["[NutritionRevamp] metabolism: 1 field(s) the step made non-finite re-stamped for a"]


def test_a_satiety_guard_restores_the_lag_it_does_not_zero():
    h = settle()
    rec = h.record("a")
    rec.satiety.L = 500.0
    h.rt.eval(WRAP)("energy.state", rec, "satiety", "L")
    next_minute(h, 4)
    assert h.NR.server.metabolism.guarded == 1
    assert rec.satiety.L == 500.0                                 # restored from its pre-step value, not stamped 0


@pytest.mark.parametrize("bad", [float("nan"), float("inf")], ids=["nan", "inf"])
@pytest.mark.parametrize("key", BUFFER_KEYS)
def test_a_bad_buffer_key_between_minutes_is_healed_and_reaches_nothing(key, bad):
    # vitC, iron and water are the keys the old six-gram list missed or let through for one minute; here every key
    h = settle()
    rec = h.record("a")
    rec.stomach.buffer.calories = 400.0
    rec.stomach.buffer.carbs = 60.0
    rec.stomach.buffer[key] = bad
    f0 = h.NR.server.kinetics.stats.failures
    next_minute(h, 4)
    assert nonfinite(rec) == [], (key, nonfinite(rec))            # the stomach is reset, the pool and nutrients clean
    assert h.NR.server.kinetics.stats.failures == f0 + 1


def test_the_next_pre_step_heal_clears_an_unguarded_field():
    h = settle()
    rec = h.record("a")
    rec.body.vStr = float("nan")                        # an input NaN between minutes: the pre-step heal's class
    next_minute(h, 4)
    assert nonfinite(rec) == []


MIRROR = r"""
function(rec)
    local NR = NutritionRevamp
    return NR.kernel.mirror.build(rec, {}, NR.data.records.ORDER)
end
"""


def build_mirror(h, rec):
    return h.rt.eval(MIRROR)(rec)


def test_a_nutrient_nan_reaches_one_mirror_then_the_heal_takes_it():
    h = settle()
    rec = h.record("a")
    h.rt.eval(WRAP)("acute.iu", rec, "nutrients.vitA", "p")
    next_minute(h, 4)
    m = build_mirror(h, rec)                            # the bus step builds before any pre-step heal
    assert m["nut_vitA_p"] != m["nut_vitA_p"]           # the documented one-minute NaN (the client blanks it)
    next_minute(h, 5)
    m = build_mirror(h, rec)
    assert math.isfinite(m["nut_vitA_p"])


def test_a_step_made_vstr_nan_never_reaches_the_mirror_doses():
    h = settle()
    rec = h.record("a")
    h.rt.eval(WRAP)("energy.state", rec, "body", "vStr")
    next_minute(h, 4)
    m = build_mirror(h, rec)
    assert math.isfinite(m["body_dStr"]) and math.isfinite(m["body_dHyp"])
    next_minute(h, 5)
    m = build_mirror(h, rec)
    assert math.isfinite(m["body_dStr"]) and math.isfinite(m["body_dHyp"])


def test_a_step_made_vhyp_nan_never_reaches_the_mirror_doses():
    h = settle()
    rec = h.record("a")
    h.rt.eval(WRAP)("energy.state", rec, "body", "vHyp")
    next_minute(h, 4)
    m = build_mirror(h, rec)
    assert math.isfinite(m["body_dStr"]) and math.isfinite(m["body_dHyp"])


# --- the writer's rows (Plan 11 Task 14): every CROSS consumer is a step that runs; the writer's rows are its reads --

SUB_PRODUCER = {"body": "metabolism", "fluids": "nutrients", "acute": "nutrients", "effects": "effects",
                "satiety": "metabolism", "stomach": "kinetics", "stomach.buffer": "kinetics"}
# Reads of a producer sub-table that need no guard: a boolean (never NaN), and the writer's own sip accumulator,
# which it reads only to add a finite sip to (it is finite by construction: K.hybrid.sip of two finite reads); the
# writer's own satiety state (P, S, the mark v and the step stamp t, ruling C-1), which no other step reads in the minute and the writer heals
# itself (W.stats.guarded, test_writer_shape.py). The writer's satiety F (W.satietyF, ruling T5-2) reads the stomach's
# liquid lane and the buffer's mass keys, each guarded by the kinetics heal (a non-finite F also falls back to
# record.stomachFill); the buffer table itself is a container read, so the test proxies it one level down.
WRITER_UNGUARDED = {"acute.frozen", "fluids.autoDrop", "satiety.P", "satiety.S", "satiety.v", "satiety.t"}

BUFFER_PROXY = r"""
function(rec, log)
    local real = rec.stomach.buffer
    rec.stomach.buffer = setmetatable({}, {
        __index = function(t, k) log[#log + 1] = "stomach.buffer." .. tostring(k); return real[k] end,
        __newindex = function(t, k, v) real[k] = v end })
end
"""

PROXY = r"""
function(rec, log)
    for _, sub in ipairs({ "body", "fluids", "acute", "effects", "satiety", "stomach" }) do
        local real = rec[sub]
        rec[sub] = setmetatable({}, {
            __index = function(t, k) log[#log + 1] = sub .. "." .. tostring(k); return real[k] end,
            __newindex = function(t, k, v) real[k] = v end })
    end
end
"""


def test_every_consumer_is_a_step_that_runs():
    h = Host()
    order = set(h.NR.server.minute.ORDER.values())
    assert {c for _, _, _, c in CROSS} - order == {"kept"}


def test_the_writers_cross_rows_are_its_reads():
    from .test_writer_shape import ENV, STATS, record
    h = Host(extra_env="NR_T = NR_T or {}\nNR_T.mode = 1\n" + ENV)
    h.fire("OnGameBoot")
    p = h.rt.eval("NR_T.statsPlayer")(h.player("a"), h.rt.eval(STATS))
    rec = record(h)
    rec.stomach = h.K.stomach.new()
    log = h.rt.table()
    h.rt.eval(BUFFER_PROXY)(rec, log)
    h.rt.eval(PROXY)(rec, log)
    h.T.age = 100.0
    h.NR.server.writer.step("a", p, rec, None)
    reads = set(log.values()) - WRITER_UNGUARDED - {"stomach.buffer"}
    rows = {s + "." + str(f) for p_, s, f, c in CROSS if c == "writer"}
    assert reads == rows
    assert all(SUB_PRODUCER[s] == p_ for p_, s, f, c in CROSS if c == "writer")
