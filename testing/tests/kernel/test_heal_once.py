"""Heal once, before the step (Plan 11 Task 12, ruling 10; Appendix J's heal1pre).

Metabolism, Nutrients and Effects heal their record sub-tables once, before the step's arithmetic. The post-step
heals are gone; in their place a post-step guard re-stamps, from its pre-step value, every field the step's own
arithmetic left non-finite that something reads before the next minute's pre-step heal. CROSS is Step 1's
enumeration of those reads: (producer step, record sub-table, field, consumer). The consumers are the steps after
the producer in NR.server.minute.ORDER (nutrients, effects, strength, weight, store), and the readers that run
before the next minute's pre-step heals: the fast clock's per-tick handler between minutes ("fast"), and the bus
step, which runs FIRST in ORDER and so reads a step-made NaN of the last minute before any heal ("bus": the push
signature and K.mirror.build); Nutrients reads record.effects at the next minute before Effects' pre-step heal.
A ring slot is a sub-table path ("body.eb7", field 7): a day close shifts slots 1-6 from pre-step-healed values,
so only slot 7 (and bandWeek's slot 7) can take a value this minute's arithmetic made.

The store step reads every K.store.INPUTS path; its rows below are the guarded inputs. An unguarded input the
step leaves non-finite is saved as a missing key (the codec writes NaN as null) and loads as its constructor's
default (K.store.load), the fresh value the heal would have stamped; body's load needs fm, lm, sex and lastAgeH
(K.store.bodyBase), so fm, lm and lastAgeH are guarded (no step writes sex).

WINDOW lists the reads left unguarded, each with the reason; the window test injects each one and shows the NaN
stays in its own field for one minute and the next pre-step heal takes it (the accepted window, ruling 10).

The injections run on the shared host; each wraps a kernel function its producer step calls near its end, so the
NaN appears inside the producer's step as its own arithmetic would make it.
"""
import math

import pytest

from .server_host import Host


def _rows(producer, sub, consumers):
    return [(producer, sub, f, c) for c, fields in consumers for f in fields]


# Step 1's table: (producer, sub-table, field, consumer).
CROSS = (
    _rows("metabolism", "body", [
        ("nutrients", ("dayIndex", "inDayClosed", "fm", "lm", "lastCloseAgeH", "eeDay", "pPrevKg", "alcDay", "met",
                       "coldMult", "carbDay", "band1Day", "band2Day")),
        ("effects", ("fm", "lm", "dayIndex", "exKcalDay", "band1Day", "band2Day", "met", "inDayClosed")),
        ("strength", ("fm", "lm", "dayIndex", "n", "nPeak", "tPeakD", "cumDef", "tDisuse")),
        ("weight", ("fm", "lm", "pDay", "carbDay", "lipDay", "ebDay", "lastCloseAgeH")),
        ("fast", ("energyState", "dmod", "rmod")),
        ("bus", ("energyState", "dmod", "rmod", "ebDay", "eeDay", "fm", "inDay", "lm", "tac")),
        ("store", ("fm", "lm", "lastAgeH", "dayIndex", "lastCloseAgeH", "inDay", "eeDay", "ebDay", "exKcalDay",
                   "pDay", "carbDay", "lipDay", "alcDay", "inDayClosed", "pPrevKg", "band1Day", "band2Day", "n",
                   "nPeak", "tPeakD", "cumDef", "tDisuse", "tac")),
    ])
    + _rows("metabolism", "body.eb7", [("nutrients", (7,)), ("weight", (7,)), ("store", (7,))])
    + _rows("metabolism", "body.carb7", [("nutrients", (7,)), ("weight", (7,)), ("store", (7,))])
    + _rows("metabolism", "body.p7", [("effects", (7,)), ("weight", (7,)), ("store", (7,))])
    + _rows("metabolism", "body.lip7", [("weight", (7,)), ("store", (7,))])
    + _rows("metabolism", "body.mass7", [("weight", (7,)), ("store", (7,))])
    + _rows("metabolism", "body.bandWeek.7", [("nutrients", (1, 2)), ("store", (1, 2))])
    + _rows("nutrients", "fluids", [
        ("effects", ("dehydPct", "naPlasma")),
        ("strength", ("dehydPct",)),
        ("fast", ("thirstTarget",)),
        ("bus", ("dehydPct", "naPlasma", "thirstTarget")),
    ])
    + _rows("nutrients", "acute", [
        ("effects", ("caf", "wd", "cafTol", "bac", "alcPeak", "hang", "bg", "iuSleep", "debtH", "iu", "exEma",
                     "bmi", "starvedDays", "coldH", "lastVigAgeH", "retEma")),
        ("strength", ("awakeH", "caf")),
        ("fast", ("S", "circ")),
        ("bus", ("awakeH", "bac", "bg", "caf", "debtH", "g", "iu", "refeedRisk")),
        ("store", ("caf", "cafTol", "alcPeak", "hang", "bg", "awakeH", "debtH", "S", "starvedDays", "bmi", "exEma",
                   "lastVigAgeH", "coldH", "retEma", "refeedRisk")),
    ])
    + _rows("nutrients", "nutrients", [("effects", ("epoch",)), ("store", ("epoch",))])
    + _rows("effects", "effects", [
        ("fast", ("fOff", "solAddH", "solMul", "stressTarget", "panicTarget", "unhappyTarget", "foodSickTarget",
                  "tempTarget", "tempAdj", "intoxTarget")),
        ("nutrients", ("mAcc", "rRec")),
        ("bus", ("epoch", "aimMul", "speedMul", "intoxTarget", "tempTarget", "healMul", "bleedMul", "infectMul",
                 "coldMul", "drain", "lethal", "stressTarget", "panicTarget", "unhappyTarget", "foodSickTarget",
                 "fOff", "mAcc", "rRec")),
        ("store", ("epoch",)),
    ])
)

# The kernel function each producer calls near its step's end: the injection lands after it returns.
NEAR_END = {"metabolism": "energy.state", "nutrients": "acute.iu", "effects": "effects.drain"}

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
    ("metabolism", "body", "vStr", "no later step reads it; Metabolism reads it next minute after its heal"),
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


def test_the_next_pre_step_heal_clears_an_unguarded_field():
    h = settle()
    rec = h.record("a")
    rec.body.vStr = float("nan")                        # an input NaN between minutes: the pre-step heal's class
    next_minute(h, 4)
    assert nonfinite(rec) == []
